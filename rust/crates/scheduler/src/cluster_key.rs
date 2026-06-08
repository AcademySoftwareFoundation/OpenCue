// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq, PartialOrd, Ord)]
pub enum TagType {
    Alloc,
    HostName,
    Manual,
    Hardware,
}

/// IDENTITY NOTE: the derived `Hash`/`PartialEq`/`Eq`/`Ord` include every field,
/// so `alloc_id` participates in tag identity. A `Tag{name, Alloc, Some(uuid)}`
/// and a `Tag{name, Alloc, None}` with the same `name`/`ttype` are *distinct*
/// keys in `BTreeSet<Tag>` and `HashMap<ClusterKey, _>`. Today the DB-loaded
/// path produces `Some(uuid)` for alloc tags and the CLI override path produces
/// `None`; the two are not mixed within a single set, so this is latent. The
/// CLI override path for alloc tags is being discontinued in the next stage,
/// after which every `TagType::Alloc` tag carries a resolved `alloc_id` and
/// this becomes a non-issue.
#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq, PartialOrd, Ord)]
pub struct Tag {
    pub name: String,
    pub ttype: TagType,
    /// `pk_alloc` (allocation UUID) when this tag was loaded as a
    /// `TagType::Alloc` cluster tag from the database. Populated by
    /// `cluster.rs::load_clusters` on the `"ALLOC"` arm and consumed by
    /// `MatchingService::process_layer` to read the per-(show, alloc)
    /// subscription burst snapshot from Redis before host checkout.
    ///
    /// `None` for non-alloc tags (manual / hostname / hardware) and for
    /// CLI-built tags where the str_tag → pk_alloc mapping isn't resolved
    /// at startup. Those paths fall back to the burst-unaware behavior.
    #[serde(default)]
    pub alloc_id: Option<Uuid>,
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

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq, PartialOrd, Ord)]
pub struct ClusterKey {
    pub facility_id: String,
    pub show_id: Uuid,
    pub tag: Tag,
}

impl std::fmt::Display for ClusterKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}:{}", self.facility_id, self.show_id, self.tag)
    }
}
