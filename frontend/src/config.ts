/**
 * IBVAP Tactical Presentation Layer Configuration
 * SIH PS-26187 | SSB, Ministry of Home Affairs
 */

// Tactical HUD corner-bracket and scanline overlay styling (pure CSS, GPU-cheap)
export const ENABLE_HUD_STYLING: boolean = true;

// Sensor skins policy (Task 7): Strictly optional, default OFF.
// When enabled, applies NVG/FLIR preview filter only with a mandatory on-screen disclaimer.
// Stored evidence video clips and SHA-256 hashes are 100% untouched.
export const ENABLE_SENSOR_SKINS: boolean = false;
