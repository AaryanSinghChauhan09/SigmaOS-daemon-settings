//! SigmaOS-daemon-settings: daemon-settings component model.

use std::collections::BTreeMap;
use std::fmt;

/// Primary domain entity for daemon-settings component.
#[derive(Debug, Clone, PartialEq)]
pub struct DaemonSettingsItem {
    pub id: String,
    pub name: String,
    pub item_type: String,
    pub enabled: bool,
}

/// Secondary domain entity for daemon-settings component.
#[derive(Debug, Clone, PartialEq)]
pub struct DaemonSettingsConfig {
    pub id: String,
    pub value: String,
    pub description: String,
}

/// Errors for the daemon-settings component domain.
#[derive(Debug, PartialEq)]
pub enum DaemonSettingsError {
    EmptyName,
    Duplicate(String),
    NotFound(String),
}

impl fmt::Display for DaemonSettingsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyName => write!(f, "name cannot be empty"),
            Self::Duplicate(id) => write!(f, "duplicate id: {id}"),
            Self::NotFound(id) => write!(f, "not found: {id}"),
        }
    }
}

impl std::error::Error for DaemonSettingsError {}

/// Registry and manager for daemon-settings component.
pub struct DaemonSettingsManager {
    pub name: String,
    items: BTreeMap<String, DaemonSettingsItem>,
    configs: BTreeMap<String, DaemonSettingsConfig>,
}

impl DaemonSettingsManager {
    /// Create a new manager instance.
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            items: BTreeMap::new(),
            configs: BTreeMap::new(),
        }
    }

    /// Add a primary item with fail-fast validation.
    pub fn add_item(&mut self, item: DaemonSettingsItem) -> Result<(), DaemonSettingsError> {
        if item.name.is_empty() {
            return Err(DaemonSettingsError::EmptyName);
        }
        if self.items.contains_key(&item.id) {
            return Err(DaemonSettingsError::Duplicate(item.id.clone()));
        }
        self.items.insert(item.id.clone(), item);
        Ok(())
    }

    /// Retrieve a primary item by id.
    pub fn get_item(&self, id: &str) -> Option<&DaemonSettingsItem> {
        self.items.get(id)
    }

    /// Count of primary items.
    pub fn count(&self) -> usize {
        self.items.len()
    }

    /// Add a secondary configuration entry.
    pub fn add_config(&mut self, cfg: DaemonSettingsConfig) {
        self.configs.insert(cfg.id.clone(), cfg);
    }

    /// Count of configuration entries.
    pub fn config_count(&self) -> usize {
        self.configs.len()
    }

    /// Enable or disable an item.
    pub fn set_enabled(&mut self, id: &str, enabled: bool) -> Result<(), DaemonSettingsError> {
        self.items
            .get_mut(id)
            .map(|item| item.enabled = enabled)
            .ok_or_else(|| DaemonSettingsError::NotFound(id.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_daemon_settings_item(id: &str, name: &str) -> DaemonSettingsItem {
        DaemonSettingsItem {
            id: id.to_string(),
            name: name.to_string(),
            item_type: "daemon-settings-default".to_string(),
            enabled: true,
        }
    }

    fn make_daemon_settings_config(id: &str, val: &str) -> DaemonSettingsConfig {
        DaemonSettingsConfig {
            id: id.to_string(),
            value: val.to_string(),
            description: format!("{} config", id),
        }
    }

    #[test]
    fn test_create_aaa() {
        let mgr = DaemonSettingsManager::new("test");
        assert_eq!(mgr.name, "test");
        assert_eq!(mgr.count(), 0);
        assert_eq!(mgr.config_count(), 0);
    }

    #[test]
    fn test_add_item_aaa() {
        let mut mgr = DaemonSettingsManager::new("test");
        let item = make_daemon_settings_item("item1", "First Item");
        assert!(mgr.add_item(item).is_ok());
        assert_eq!(mgr.count(), 1);
    }

    #[test]
    fn test_empty_name_rejected_aaa() {
        let mut mgr = DaemonSettingsManager::new("test");
        let item = make_daemon_settings_item("item1", "");
        assert_eq!(mgr.add_item(item), Err(DaemonSettingsError::EmptyName));
    }

    #[test]
    fn test_duplicate_rejected_aaa() {
        let mut mgr = DaemonSettingsManager::new("test");
        let item1 = make_daemon_settings_item("item1", "First");
        let item2 = make_daemon_settings_item("item1", "Duplicate");
        mgr.add_item(item1).unwrap();
        assert_eq!(mgr.add_item(item2), Err(DaemonSettingsError::Duplicate("item1".to_string())));
    }

    #[test]
    fn test_config_addition_aaa() {
        let mut mgr = DaemonSettingsManager::new("test");
        let cfg = make_daemon_settings_config("cfg1", "value1");
        mgr.add_config(cfg);
        assert_eq!(mgr.config_count(), 1);
    }

    #[test]
    fn test_get_item_aaa() {
        let mut mgr = DaemonSettingsManager::new("test");
        let item = make_daemon_settings_item("item1", "First Item");
        mgr.add_item(item).unwrap();
        assert!(mgr.get_item("item1").is_some());
        assert!(mgr.get_item("none").is_none());
    }

    #[test]
    fn test_set_enabled_aaa() {
        let mut mgr = DaemonSettingsManager::new("test");
        let item = make_daemon_settings_item("item1", "First Item");
        mgr.add_item(item).unwrap();
        assert!(mgr.set_enabled("item1", false).is_ok());
        assert!(!mgr.get_item("item1").unwrap().enabled);
        assert_eq!(mgr.set_enabled("none", true), Err(DaemonSettingsError::NotFound("none".to_string())));
    }
}
