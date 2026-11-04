use anyhow::Result;
use sigmaos_component::{Config, Service};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_aaa() -> Result<()> {
        let config = Config::default();
        assert!(config.process().is_ok());
        Ok(())
    }

    #[test]
    fn test_service_lifecycle_aaa() -> Result<()> {
        let config = Config::default();
        let mut service = Service::new(config);
        assert!(!service.is_running());
        service.start()?;
        assert!(service.is_running());
        assert!(service.start().is_err());
        service.stop()?;
        assert!(!service.is_running());
        assert!(service.stop().is_err());
        Ok(())
    }
}
