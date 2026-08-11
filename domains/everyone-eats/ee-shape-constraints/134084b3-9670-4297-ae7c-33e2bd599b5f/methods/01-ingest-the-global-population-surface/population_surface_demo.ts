// Demo specimen for: Ingest the global population surface
export function ingestGlobalPopulationSurface(sources, coverage) {
  const datedCounts = loadPopulationCounts(sources)
  const administrativeGeometry = loadAdministrativeGeometry(coverage)
  return preserveUncertainty({ datedCounts, administrativeGeometry })
}
