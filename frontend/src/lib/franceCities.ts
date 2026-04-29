// ═══════════════════════════════════════════════════════════════════════
//  103 villes principales de France métropolitaine + Corse
//  Coordonnées GPS réelles (source : Wikipédia / data.gouv.fr)
//  Utilisé pour l'affichage des marqueurs sur FranceMap
// ═══════════════════════════════════════════════════════════════════════

export interface FrenchCity {
  name: string
  lat: number
  lon: number
}

export const FRANCE_CITIES: FrenchCity[] = [
  // ─── Hauts-de-France ───────────────────────────────────────────────
  { name: "Calais",                lat: 50.948,  lon: 1.858  },
  { name: "Boulogne-sur-Mer",      lat: 50.726,  lon: 1.614  },
  { name: "Berck",                 lat: 50.405,  lon: 1.578  },
  { name: "Lille",                 lat: 50.629,  lon: 3.057  },
  { name: "Maubeuge",              lat: 50.279,  lon: 3.972  },
  { name: "Saint-Quentin",         lat: 49.847,  lon: 3.287  },
  { name: "Amiens",                lat: 49.894,  lon: 2.296  },
  { name: "Compiègne",             lat: 49.418,  lon: 2.826  },
  { name: "Beauvais",              lat: 49.430,  lon: 2.081  },

  // ─── Normandie ─────────────────────────────────────────────────────
  { name: "Cherbourg",             lat: 49.640,  lon: -1.616 },
  { name: "Le Havre",              lat: 49.494,  lon: 0.108  },
  { name: "Dieppe",                lat: 49.923,  lon: 1.079  },
  { name: "Rouen",                 lat: 49.443,  lon: 1.099  },
  { name: "Saint-Lô",              lat: 49.117,  lon: -1.085 },
  { name: "Bernay",                lat: 49.090,  lon: 0.598  },
  { name: "Flers",                 lat: 48.749,  lon: -0.566 },

  // ─── Île-de-France ─────────────────────────────────────────────────
  { name: "Paris",                 lat: 48.857,  lon: 2.352  },
  { name: "Chartres",              lat: 48.444,  lon: 1.490  },
  { name: "Montereau-Faut-Yonne",  lat: 48.387,  lon: 2.954  },

  // ─── Grand Est ─────────────────────────────────────────────────────
  { name: "Charleville-Mézières",  lat: 49.770,  lon: 4.720  },
  { name: "Reims",                 lat: 49.258,  lon: 4.032  },
  { name: "Verdun",                lat: 49.160,  lon: 5.385  },
  { name: "Forbach",               lat: 49.189,  lon: 6.900  },
  { name: "Metz",                  lat: 49.119,  lon: 6.176  },
  { name: "Sarrebourg",            lat: 48.736,  lon: 7.058  },
  { name: "Saint-Dizier",          lat: 48.638,  lon: 4.949  },
  { name: "Strasbourg",            lat: 48.583,  lon: 7.745  },
  { name: "Épinal",                lat: 48.173,  lon: 6.450  },
  { name: "Troyes",                lat: 48.297,  lon: 4.075  },
  { name: "Chaumont",              lat: 48.111,  lon: 5.140  },
  { name: "Mulhouse",              lat: 47.750,  lon: 7.336  },

  // ─── Bretagne ──────────────────────────────────────────────────────
  { name: "Lannion",               lat: 48.732,  lon: -3.460 },
  { name: "Saint-Malo",            lat: 48.649,  lon: -2.025 },
  { name: "Brest",                 lat: 48.391,  lon: -4.486 },
  { name: "Saint-Brieuc",          lat: 48.514,  lon: -2.766 },
  { name: "Rennes",                lat: 48.117,  lon: -1.677 },
  { name: "Lorient",               lat: 47.747,  lon: -3.367 },

  // ─── Pays de la Loire ──────────────────────────────────────────────
  { name: "Laval",                 lat: 48.071,  lon: -0.770 },
  { name: "Le Mans",               lat: 47.998,  lon: 0.198  },
  { name: "Angers",                lat: 47.470,  lon: -0.553 },
  { name: "Nantes",                lat: 47.218,  lon: -1.553 },
  { name: "La Baule-Escoublac",    lat: 47.286,  lon: -2.391 },
  { name: "La Roche-sur-Yon",      lat: 46.670,  lon: -1.426 },
  { name: "Bressuire",             lat: 46.840,  lon: -0.488 },

  // ─── Centre-Val de Loire ───────────────────────────────────────────
  { name: "Orléans",               lat: 47.902,  lon: 1.909  },
  { name: "Montargis",             lat: 48.000,  lon: 2.733  },
  { name: "Tours",                 lat: 47.394,  lon: 0.685  },
  { name: "Bourges",               lat: 47.082,  lon: 2.398  },
  { name: "Romorantin-Lanthenay",  lat: 47.358,  lon: 1.738  },
  { name: "Châteauroux",           lat: 46.811,  lon: 1.690  },

  // ─── Bourgogne-Franche-Comté ───────────────────────────────────────
  { name: "Dijon",                 lat: 47.322,  lon: 5.041  },
  { name: "Chalon-sur-Saône",      lat: 46.781,  lon: 4.854  },
  { name: "Lons-le-Saunier",       lat: 46.674,  lon: 5.554  },
  { name: "Belfort",               lat: 47.638,  lon: 6.864  },
  { name: "Nevers",                lat: 46.989,  lon: 3.158  },
  { name: "Bourg-en-Bresse",       lat: 46.205,  lon: 5.226  },
  { name: "Roanne",                lat: 46.034,  lon: 4.069  },

  // ─── Nouvelle-Aquitaine ────────────────────────────────────────────
  { name: "La Rochelle",           lat: 46.160,  lon: -1.151 },
  { name: "Niort",                 lat: 46.323,  lon: -0.464 },
  { name: "Saintes",               lat: 45.747,  lon: -0.633 },
  { name: "Poitiers",              lat: 46.581,  lon: 0.339  },
  { name: "Limoges",               lat: 45.833,  lon: 1.262  },
  { name: "Guéret",                lat: 46.171,  lon: 1.870  },
  { name: "Ussel",                 lat: 45.553,  lon: 2.314  },
  { name: "Angoulême",             lat: 45.648,  lon: 0.156  },
  { name: "Périgueux",             lat: 45.184,  lon: 0.722  },
  { name: "Brive-la-Gaillarde",    lat: 45.158,  lon: 1.534  },
  { name: "Bordeaux",              lat: 44.838,  lon: -0.578 },
  { name: "Agen",                  lat: 44.205,  lon: 0.616  },
  { name: "Mont-de-Marsan",        lat: 43.890,  lon: -0.498 },
  { name: "Bayonne",               lat: 43.493,  lon: -1.475 },
  { name: "Pau",                   lat: 43.295,  lon: -0.371 },

  // ─── Auvergne-Rhône-Alpes ──────────────────────────────────────────
  { name: "Montluçon",             lat: 46.341,  lon: 2.601  },
  { name: "Le Puy-en-Velay",       lat: 45.043,  lon: 3.886  },
  { name: "Aurillac",              lat: 44.929,  lon: 2.444  },
  { name: "Lyon",                  lat: 45.764,  lon: 4.836  },
  { name: "Annecy",                lat: 45.900,  lon: 6.129  },
  { name: "Thonon-les-Bains",      lat: 46.371,  lon: 6.479  },
  { name: "Grenoble",              lat: 45.188,  lon: 5.724  },
  { name: "Valence",               lat: 44.933,  lon: 4.892  },
  { name: "Briançon",              lat: 44.898,  lon: 6.640  },
  { name: "Gap",                   lat: 44.560,  lon: 6.082  },

  // ─── Occitanie ─────────────────────────────────────────────────────
  { name: "Cahors",                lat: 44.448,  lon: 1.441  },
  { name: "Figeac",                lat: 44.608,  lon: 2.034  },
  { name: "Rodez",                 lat: 44.351,  lon: 2.575  },
  { name: "Mende",                 lat: 44.518,  lon: 3.500  },
  { name: "Albi",                  lat: 43.929,  lon: 2.148  },
  { name: "Alès",                  lat: 44.126,  lon: 4.083  },
  { name: "Auch",                  lat: 43.646,  lon: 0.586  },
  { name: "Toulouse",              lat: 43.605,  lon: 1.444  },
  { name: "Carcassonne",           lat: 43.213,  lon: 2.353  },
  { name: "Saint-Gaudens",         lat: 43.107,  lon: 0.722  },
  { name: "Foix",                  lat: 42.965,  lon: 1.605  },
  { name: "Béziers",               lat: 43.345,  lon: 3.215  },
  { name: "Montpellier",           lat: 43.611,  lon: 3.877  },
  { name: "Perpignan",             lat: 42.698,  lon: 2.895  },

  // ─── Provence-Alpes-Côte d'Azur ────────────────────────────────────
  { name: "Avignon",               lat: 43.949,  lon: 4.806  },
  { name: "Manosque",              lat: 43.829,  lon: 5.785  },
  { name: "Marseille",             lat: 43.296,  lon: 5.370  },
  { name: "Hyères",                lat: 43.121,  lon: 6.130  },
  { name: "Nice",                  lat: 43.703,  lon: 7.266  },

  // ─── Corse ─────────────────────────────────────────────────────────
  { name: "Bastia",                lat: 42.697,  lon: 9.450  },
  { name: "Ajaccio",               lat: 41.928,  lon: 8.738  },
]
