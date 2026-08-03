use std::any::{Any, TypeId};
use std::collections::HashMap;
use std::sync::Arc;

/// Type-safe container for application state
#[derive(Default)]
pub struct StateContainer {
    items: HashMap<TypeId, Arc<dyn Any + Send + Sync>>,
}

impl StateContainer {
    pub fn new() -> Self {
        StateContainer {
            items: HashMap::new(),
        }
    }

    /// Insert a value into the state container
    pub fn insert<T: Send + Sync + 'static>(&mut self, value: T) {
        self.items.insert(TypeId::of::<T>(), Arc::new(value));
    }

    /// Get a reference to a value from the state container
    pub fn get<T: Send + Sync + 'static>(&self) -> Option<Arc<T>> {
        self.items
            .get(&TypeId::of::<T>())
            .and_then(|v| v.clone().downcast::<T>().ok())
    }
}

/// A reference to managed application state of type `T`
///
/// Can be used as a handler parameter to access shared state:
/// ```ignore
/// #[get("/count")]
/// fn counter(state: &State<Counter>) -> String { ... }
/// ```
pub struct State<T: Send + Sync + 'static> {
    inner: Arc<T>,
}

impl<T: Send + Sync + 'static> State<T> {
    pub fn new(inner: Arc<T>) -> Self {
        State { inner }
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }
}

impl<T: Send + Sync + 'static> std::ops::Deref for State<T> {
    type Target = T;
    fn deref(&self) -> &Self::Target {
        &self.inner
    }
}

impl<T: Send + Sync + 'static> Clone for State<T> {
    fn clone(&self) -> Self {
        State {
            inner: self.inner.clone(),
        }
    }
}
