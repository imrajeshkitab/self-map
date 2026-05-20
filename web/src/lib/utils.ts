import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export const PRESET_PLACES = [
  { name: "Gachibowli, Hyderabad",   lat: 17.4399, lon: 78.3489 },
  { name: "Hyderabad (city center)", lat: 17.3850, lon: 78.4867 },
  { name: "Bangalore",               lat: 12.9716, lon: 77.5946 },
  { name: "Mumbai",                  lat: 19.0760, lon: 72.8777 },
  { name: "Delhi",                   lat: 28.6139, lon: 77.2090 },
  { name: "Chennai",                 lat: 13.0827, lon: 80.2707 },
  { name: "Kolkata",                 lat: 22.5726, lon: 88.3639 },
  { name: "Pune",                    lat: 18.5204, lon: 73.8567 },
];

export const PLANET_ABBR: Record<string, string> = {
  Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju",
  Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke",
};

export const SIGNS = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
];

// South-Indian style 4×4 grid — each sign sits in a fixed cell.
// [row, col] (1-indexed)
export const SIGN_POS: Record<string, [number, number]> = {
  Pisces:      [1, 1], Aries:       [1, 2], Taurus:      [1, 3], Gemini:      [1, 4],
  Cancer:      [2, 4], Leo:         [3, 4], Virgo:       [4, 4], Libra:       [4, 3],
  Scorpio:     [4, 2], Sagittarius: [4, 1], Capricorn:   [3, 1], Aquarius:    [2, 1],
};
