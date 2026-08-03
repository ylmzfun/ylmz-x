use ylmz::prelude::*;
use ylmz::Config;
use serde::{Deserialize, Serialize};

// ===== State =====

#[derive(Default)]
struct HitCounter {
    count: std::sync::atomic::AtomicU64,
}

impl HitCounter {
    fn increment(&self) -> u64 {
        self.count.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1
    }
}

// ===== Routes =====

#[get("/")]
fn index() -> &'static str {
    "Hello, ylmz! 🚀\n\
     Try these routes:\n\
     GET  /hello/<name>\n\
     GET  /hello/<name>/<age>\n\
     GET  /search?q=<query>\n\
     POST /api/users  (JSON body)\n\
     GET  /counter\n\
     GET  /health"
}

#[get("/hello/<name>")]
fn hello(name: String) -> String {
    format!("Hello, {}! Welcome to ylmz.", name)
}

#[get("/hello/<name>/<age>")]
fn hello_age(name: String, age: u32) -> String {
    if age >= 18 {
        format!("Hello, {}! At {} you're an adult.", name, age)
    } else {
        format!("Hey, {}! At {} you're still young.", name, age)
    }
}

#[get("/search")]
fn search(query: Query<SearchParams>) -> String {
    let params = query.into_inner();
    format!(
        "Search results for '{}' (page {})",
        params.q,
        params.page.unwrap_or(1)
    )
}

#[derive(Debug, Deserialize)]
struct SearchParams {
    q: String,
    page: Option<u32>,
}

#[get("/counter")]
fn counter(state: State<HitCounter>) -> String {
    let count = state.increment();
    format!("Hit count: {}", count)
}

#[get("/health")]
fn health() -> (Status, &'static str) {
    (Status::OK, "OK")
}

// ===== JSON API =====

#[derive(Debug, Deserialize, Serialize)]
struct User {
    name: String,
    email: String,
}

#[post("/api/users", data = "<user>")]
fn create_user(user: Json<User>) -> Json<User> {
    println!("Creating user: {} <{}>", user.0.name, user.0.email);
    user
}

// ===== Error Catchers =====

#[catch(404)]
fn not_found() -> (Status, String) {
    (
        Status::NOT_FOUND,
        "{\"error\": \"Not Found\", \"message\": \"The requested resource does not exist.\"}".into(),
    )
}

#[catch(500)]
fn internal_error() -> (Status, String) {
    (
        Status::INTERNAL_SERVER_ERROR,
        "{\"error\": \"Internal Server Error\"}".into(),
    )
}

// ===== Main =====

fn main() -> ylmz::Result<()> {
    println!("╔══════════════════════════════════╗");
    println!("║   ylmz — Rocket-inspired Rust   ║");
    println!("║      Web Framework Demo          ║");
    println!("╚══════════════════════════════════╝\n");

    App::new()
        .manage(HitCounter::default())
        .attach(Logger)
        .register("/", catchers![not_found, internal_error])
        .mount("/", routes![index, hello, hello_age, search, counter, health])
        .mount("/", routes![create_user])
        .configure(
            Config::new()
                .address("127.0.0.1")
                .port(8000),
        )
        .launch()
}
