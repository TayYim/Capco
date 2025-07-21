/**
 * Frontend name generator for creating memorable experiment names.
 * 
 * Generates human-friendly names by combining adjectives and animals/objects
 * to make experiments easily identifiable and memorable.
 */

// Lists of adjectives and animals for name generation
const ADJECTIVES = [
  "Agile", "Bold", "Clever", "Dynamic", "Elegant", "Fast", "Graceful", "Heavy",
  "Intelligent", "Jolly", "Keen", "Lightning", "Mighty", "Noble", "Optimized",
  "Precise", "Quick", "Robust", "Swift", "Turbulent", "Ultra", "Vibrant",
  "Wild", "Zenial", "Youthful", "Zealous", "Active", "Brave", "Careful",
  "Daring", "Epic", "Fearless", "Giant", "Heroic", "Intense", "Joyful",
  "Kind", "Legendary", "Majestic", "Nimble", "Outstanding", "Powerful"
];

const ANIMALS = [
  "Falcon", "Tiger", "Eagle", "Wolf", "Lion", "Shark", "Panther", "Cheetah",
  "Hawk", "Bear", "Fox", "Lynx", "Jaguar", "Leopard", "Raven", "Phoenix",
  "Dragon", "Griffin", "Viper", "Cobra", "Stallion", "Mustang", "Bronco",
  "Rhino", "Bison", "Moose", "Elk", "Deer", "Gazelle", "Antelope",
  "Dolphin", "Whale", "Orca", "Badger", "Wolverine", "Otter", "Beaver"
];

const TECH_ADJECTIVES = [
  "Quantum", "Neural", "Binary", "Digital", "Cyber", "Virtual", "Matrix",
  "Nano", "Micro", "Mega", "Turbo", "Hyper", "Ultra", "Meta", "Proto",
  "Alpha", "Beta", "Gamma", "Delta", "Omega", "Prime", "Core", "Edge"
];

const OBJECTS = [
  "Quest", "Mission", "Trial", "Test", "Probe", "Scan", "Search", "Hunt",
  "Explorer", "Finder", "Seeker", "Scout", "Tracker", "Analyzer", "Monitor",
  "Detector", "Sensor", "Engine", "Runner", "Walker", "Driver", "Pilot"
];

export type NameStyle = "animal" | "tech" | "mixed";

/**
 * Generate a random experiment name.
 */
export function generateExperimentName(style: NameStyle = "animal"): string {
  if (style === "tech") {
    return `${getRandomItem(TECH_ADJECTIVES)} ${getRandomItem(OBJECTS)}`;
  } else if (style === "mixed") {
    // Randomly choose between animal and tech style
    if (Math.random() < 0.7) {
      return `${getRandomItem(ADJECTIVES)} ${getRandomItem(ANIMALS)}`;
    } else {
      return `${getRandomItem(TECH_ADJECTIVES)} ${getRandomItem(OBJECTS)}`;
    }
  } else {
    // Default "animal" style
    return `${getRandomItem(ADJECTIVES)} ${getRandomItem(ANIMALS)}`;
  }
}

/**
 * Generate a unique experiment name not in the existing set.
 */
export function generateUniqueName(
  existingNames: Set<string> = new Set(),
  style: NameStyle = "animal",
  maxAttempts: number = 100
): string {
  for (let i = 0; i < maxAttempts; i++) {
    const name = generateExperimentName(style);
    if (!existingNames.has(name)) {
      return name;
    }
  }

  // If we can't find a unique name, add a number suffix
  const baseName = generateExperimentName(style);
  let counter = 1;
  while (existingNames.has(`${baseName} #${counter}`)) {
    counter++;
  }

  return `${baseName} #${counter}`;
}

/**
 * Validate an experiment name.
 */
export function validateExperimentName(name: string): { isValid: boolean; error?: string } {
  if (!name || !name.trim()) {
    return { isValid: false, error: "Name cannot be empty" };
  }

  if (name.trim().length < 2) {
    return { isValid: false, error: "Name must be at least 2 characters long" };
  }

  if (name.trim().length > 100) {
    return { isValid: false, error: "Name must be less than 100 characters" };
  }

  // Check for invalid characters (basic validation)
  const invalidChars = /[<>:"/\\|?*]/;
  if (invalidChars.test(name)) {
    return { isValid: false, error: "Name cannot contain these characters: < > : \" / \\ | ? *" };
  }

  return { isValid: true };
}

/**
 * Get suggestions for experiment names based on scenario type.
 */
export function suggestNamesForScenario(scenarioType: string = "general", count: number = 5): string[] {
  const suggestions: string[] = [];

  // Predefined suggestions for common scenarios
  const scenarioNames: Record<string, string[]> = {
    collision: ["Crash Hunter", "Impact Seeker", "Collision Finder", "Safety Probe"],
    performance: ["Speed Demon", "Performance Beast", "Turbo Scanner", "Quick Explorer"],
    safety: ["Guardian Angel", "Safety Shield", "Protective Eagle", "Secure Falcon"],
    stress: ["Pressure Test", "Stress Warrior", "Endurance Tiger", "Limit Pusher"]
  };

  // Add predefined suggestions if available
  if (scenarioNames[scenarioType]) {
    suggestions.push(...scenarioNames[scenarioType]);
  }

  // Fill remaining slots with random names
  const existingSet = new Set(suggestions);
  while (suggestions.length < count) {
    let name: string;
    if (scenarioType.includes("collision") || scenarioType.includes("crash")) {
      // Use more aggressive adjectives for collision scenarios
      const aggressiveAdj = ["Fierce", "Brutal", "Intense", "Savage", "Violent", "Crushing"];
      name = `${getRandomItem(aggressiveAdj)} ${getRandomItem(ANIMALS)}`;
    } else {
      name = generateExperimentName("mixed");
    }

    if (!existingSet.has(name)) {
      suggestions.push(name);
      existingSet.add(name);
    }
  }

  return suggestions.slice(0, count);
}

/**
 * Helper function to get a random item from an array.
 */
function getRandomItem<T>(array: T[]): T {
  return array[Math.floor(Math.random() * array.length)];
} 