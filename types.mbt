pub const StatusOK = 200
pub const StatusCreated = 201
pub const StatusNoContent = 204
pub const StatusBadRequest = 400
pub const StatusUnauthorized = 401
pub const StatusForbidden = 403
pub const StatusNotFound = 404
pub const StatusMethodNotAllowed = 405
pub const StatusInternalServerError = 500

pub struct Param {
  key : String
  value : String
}
pub struct Params(Array[Param])

pub fn Params::get(self : Params, key : String) -> String? {
  for i = 0; i < self.0.length(); i = i + 1 {
    if self.0[i].key == key { return Some(self.0[i].value) }
  }
  None
}

pub struct Request {
  http_method : String
  path : String
  query : String
  headers : Map[String, String]
  body : String
}

pub struct ResponseWriter {
  status : Int
  headers : Map[String, String]
  body : String
  written : Bool
}

pub fn ResponseWriter::new() -> ResponseWriter {
  { status: StatusOK, headers: {}, body: "", written: false }
}
pub struct Context {
  request : Request
  writer : ResponseWriter
  params : Params
  handlers : Array[(Context) -> Context]
  index : Int
  keys : Map[String, String]
  aborted : Bool
  errors : Array[String]
}


pub type HandlerFunc = (Context) -> Context
