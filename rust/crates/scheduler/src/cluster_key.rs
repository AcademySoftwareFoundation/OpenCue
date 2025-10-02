use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq)]
pub enum TagType {
    Alloc,
    HostName,
    Manual,
}

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq)]
pub struct Tag {
    pub name: String,
    pub ttype: TagType,
}

impl std::ops::Deref for Tag {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        &self.name
    }
}

impl std::fmt::Display for Tag {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.name)
    }
}

impl AsRef<str> for Tag {
    fn as_ref(&self) -> &str {
        &self.name
    }
}

impl std::borrow::Borrow<str> for Tag {
    fn borrow(&self) -> &str {
        &self.name
    }
}

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq)]
pub struct ClusterKey {
    pub facility_id: String,
    pub show_id: String,
    pub tag: Tag,
}

impl std::fmt::Display for ClusterKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}:{}", self.facility_id, self.show_id, self.tag)
    }
}
