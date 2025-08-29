use uuid::Uuid;

#[derive(Debug, Clone, Hash, PartialEq, Eq)]
pub struct ClusterKey {
    pub facility_show: Option<(Uuid, Uuid)>,
    pub tag: String,
}

impl std::fmt::Display for ClusterKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match &self.facility_show {
            Some(facility_show) => {
                write!(f, "{}:{}:{}", facility_show.0, facility_show.1, self.tag)
            }
            None => write!(f, "{}", self.tag),
        }
    }
}

impl ClusterKey {
    pub fn is_custom_tag(&self) -> bool {
        self.facility_show.is_none()
    }
}
