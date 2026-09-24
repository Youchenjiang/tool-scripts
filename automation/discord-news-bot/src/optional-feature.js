async function initializeOptionalFeature(name, setup, logger = console) {
  try {
    return await setup();
  } catch (error) {
    logger.error(`[${name} setup] ${error.stack || error.message}`);
    return undefined;
  }
}

module.exports = { initializeOptionalFeature };
