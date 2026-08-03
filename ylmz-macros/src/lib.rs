use proc_macro::TokenStream;
use quote::{format_ident, quote};
use syn::{
    parse::{Parse, ParseStream},
    parse_macro_input, FnArg, ItemFn, PatType, Type,
};

/// Parsed arguments for a route attribute like `#[get("/path/<param>", data = "<body>")]`
struct RouteArgs {
    path: String,
    data_param: Option<String>,
}

impl Parse for RouteArgs {
    fn parse(input: ParseStream) -> syn::Result<Self> {
        // First token is the path string literal
        let path_lit: syn::LitStr = input.parse()?;
        let path = path_lit.value();

        let mut data_param = None;

        // Check for additional args like `data = "<name>"`
        if input.peek(syn::Token![,]) {
            let _: syn::Token![,] = input.parse()?;

            // Try to parse `data = "<name>"`
            let ident: syn::Ident = input.parse()?;
            if ident == "data" {
                let _: syn::Token![=] = input.parse()?;
                let data_lit: syn::LitStr = input.parse()?;
                let data_val = data_lit.value();
                // Strip angle brackets if present (e.g., "<body>" → "body")
                data_param = Some(
                    data_val
                        .strip_prefix('<')
                        .and_then(|s| s.strip_suffix('>'))
                        .unwrap_or(&data_val)
                        .to_string(),
                );
            }
        }

        Ok(RouteArgs { path, data_param })
    }
}

/// Parse the path to extract `<param>` names (path parameters)
fn parse_path_params(path: &str) -> Vec<String> {
    path.split('/')
        .filter(|seg| seg.starts_with('<') && seg.ends_with('>'))
        .map(|seg| seg[1..seg.len() - 1].to_string())
        .collect()
}

/// Check if a type matches a simple pattern like `Json<T>`, `Query<T>`, `State<T>`
fn type_is(type_: &Type, wrapper: &str) -> bool {
    if let Type::Path(type_path) = type_ {
        if let Some(segment) = type_path.path.segments.last() {
            return segment.ident == wrapper;
        }
    }
    false
}

/// Check if type is `&State<T>` (reference to State)
fn type_is_ref_state(type_: &Type) -> bool {
    if let Type::Reference(ref_type) = type_ {
        return type_is(&ref_type.elem, "State");
    }
    false
}

/// Generate extraction code for a single function parameter.
/// Returns (extraction_stmt, call_arg_ident)
fn generate_extraction(
    arg: &PatType,
    path_params: &[String],
    param_index: &mut usize,
    data_param: Option<&str>,
) -> (proc_macro2::TokenStream, proc_macro2::TokenStream) {
    let pat = &arg.pat;
    let ty = &arg.ty;

    // Check if this is a reference to &State<T> (e.g., `state: &State<Counter>`)
    if type_is_ref_state(ty) {
        return (
            quote! {
                let #pat = <#ty as ylmz::FromRequest>::from_request(req, state)?;
            },
            quote! { #pat },
        );
    }

    // Check if type is State<T> (e.g., `state: State<Counter>`)
    if type_is(ty, "State") {
        return (
            quote! {
                let #pat = <#ty as ylmz::FromRequest>::from_request(req, state)?;
            },
            quote! { #pat },
        );
    }

    // Check if type is Query<T>
    if type_is(ty, "Query") {
        return (
            quote! {
                let #pat = <#ty as ylmz::FromRequest>::from_request(req, state)?;
            },
            quote! { #pat },
        );
    }

    // Check if type is Json<T>
    if type_is(ty, "Json") {
        return (
            quote! {
                let #pat = <#ty as ylmz::FromRequest>::from_request(req, state)?;
            },
            quote! { #pat },
        );
    }

    // Check if this is the data (body) parameter by name
    if let Some(data_name) = data_param {
        if let syn::Pat::Ident(pat_ident) = pat.as_ref() {
            if pat_ident.ident == data_name {
                return (
                    quote! {
                        let #pat = <#ty as ylmz::FromRequest>::from_request(req, state)?;
                    },
                    quote! { #pat },
                );
            }
        }
    }

    // Otherwise, treat as positional path parameter
    if *param_index < path_params.len() {
        let param_name = &path_params[*param_index];
        *param_index += 1;

        // For String type, just extract directly
        if type_is(ty, "String") {
            return (
                quote! {
                    let #pat = ylmz::extractor::extract_path_string(req, #param_name)?;
                },
                quote! { #pat },
            );
        }

        // For other types, use parse
        return (
            quote! {
                let #pat = ylmz::extractor::extract_path_param::<#ty>(req, #param_name)?;
            },
            quote! { #pat },
        );
    }

    // Fallback — shouldn't happen with well-formed routes
    (
        quote! {
            compile_error!("Too many function parameters for route path parameters");
        },
        quote! { unreachable!() },
    )
}

/// Generate the route wrapper function for a handler
fn generate_route(
    attr: &RouteArgs,
    func: &ItemFn,
    method_name: &str,
) -> proc_macro2::TokenStream {
    let func_name = &func.sig.ident;
    let route_fn_name = format_ident!("_ylmz_route_{}", func_name);
    let path = &attr.path;
    let method_ident = format_ident!("{}", method_name);

    let path_params = parse_path_params(path);
    let data_param = attr.data_param.as_deref();

    // Generate extraction code for each parameter
    let mut extractions = Vec::new();
    let mut call_args = Vec::new();
    let mut param_index = 0;

    for arg in &func.sig.inputs {
        if let FnArg::Typed(pat_type) = arg {
            let (extract, arg_ident) = generate_extraction(
                pat_type,
                &path_params,
                &mut param_index,
                data_param,
            );
            extractions.push(extract);
            call_args.push(arg_ident);
        }
    }

    let handler_body = quote! {{
        #(#extractions)*
        let __result = #func_name(#(#call_args),*);
        Ok(ylmz::Responder::respond_to(__result))
    }};

    quote! {
        #[allow(non_snake_case)]
        pub fn #route_fn_name() -> ylmz::Route {
            ylmz::Route::new(
                ylmz::Method::#method_ident,
                #path,
                ::std::boxed::Box::new(|req: &mut ylmz::Request, state: &ylmz::StateContainer| -> ylmz::Result<ylmz::Response> {
                    #handler_body
                }),
            )
        }
    }
}

/// Shared route macro implementation
fn route_macro(attr: TokenStream, item: TokenStream, method: &str) -> TokenStream {
    let args = parse_macro_input!(attr as RouteArgs);
    let func = parse_macro_input!(item as ItemFn);
    let original_func = func.clone();

    let route_gen = generate_route(&args, &func, method);

    let expanded = quote! {
        #original_func
        #route_gen
    };

    expanded.into()
}

/// `#[get("/path/<param>")]` — HTTP GET route
#[proc_macro_attribute]
pub fn get(attr: TokenStream, item: TokenStream) -> TokenStream {
    route_macro(attr, item, "GET")
}

/// `#[post("/path", data = "<body>")]` — HTTP POST route
#[proc_macro_attribute]
pub fn post(attr: TokenStream, item: TokenStream) -> TokenStream {
    route_macro(attr, item, "POST")
}

/// `#[put("/path/<id>", data = "<body>")]` — HTTP PUT route
#[proc_macro_attribute]
pub fn put(attr: TokenStream, item: TokenStream) -> TokenStream {
    route_macro(attr, item, "PUT")
}

/// `#[delete("/path/<id>")]` — HTTP DELETE route
#[proc_macro_attribute]
pub fn delete(attr: TokenStream, item: TokenStream) -> TokenStream {
    route_macro(attr, item, "DELETE")
}

/// `#[patch("/path/<id>", data = "<body>")]` — HTTP PATCH route
#[proc_macro_attribute]
pub fn patch(attr: TokenStream, item: TokenStream) -> TokenStream {
    route_macro(attr, item, "PATCH")
}

// ===== #[catch] =====

struct CatchArgs {
    code: u16,
}

impl Parse for CatchArgs {
    fn parse(input: ParseStream) -> syn::Result<Self> {
        let lit: syn::LitInt = input.parse()?;
        Ok(CatchArgs {
            code: lit.base10_parse()?,
        })
    }
}

/// `#[catch(404)]` — Error catcher
#[proc_macro_attribute]
pub fn catch(attr: TokenStream, item: TokenStream) -> TokenStream {
    let args = parse_macro_input!(attr as CatchArgs);
    let func = parse_macro_input!(item as ItemFn);
    let original_func = func.clone();
    let func_name = &func.sig.ident;
    let catcher_fn_name = format_ident!("_ylmz_catcher_{}", func_name);
    let code = args.code;

    let expanded = quote! {
        #original_func

        #[allow(non_snake_case)]
        pub fn #catcher_fn_name() -> ylmz::Catcher {
            ylmz::Catcher::new(
                #code,
                ::std::boxed::Box::new(move |_status: &ylmz::Status| {
                    let result = #func_name();
                    ylmz::Responder::respond_to(result)
                }),
            )
        }
    };

    expanded.into()
}
