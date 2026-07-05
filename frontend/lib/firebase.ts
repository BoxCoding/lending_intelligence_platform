/**
 * Firebase web SDK bootstrap (client side).
 *
 * Used for Analytics (and future Firebase Auth). Firestore DATA is served
 * by the FastAPI backend through the Admin SDK — the browser never reads
 * Firestore directly, so security rules can stay locked down.
 *
 * All values come from NEXT_PUBLIC_* env vars so nothing is hard-coded;
 * if the API key is absent the module becomes a no-op and the app works
 * exactly as before.
 */
import { getApps, initializeApp, type FirebaseApp } from "firebase/app";
import { getAnalytics, isSupported, logEvent, type Analytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

let app: FirebaseApp | null = null;
let analytics: Analytics | null = null;

export function getFirebaseApp(): FirebaseApp | null {
  if (typeof window === "undefined" || !firebaseConfig.apiKey) return null;
  if (!app) app = getApps()[0] ?? initializeApp(firebaseConfig);
  return app;
}

/** Initialise Analytics once per session (browser only, if supported). */
export async function initAnalytics(): Promise<Analytics | null> {
  const fb = getFirebaseApp();
  if (!fb || analytics) return analytics;
  if (await isSupported().catch(() => false)) {
    analytics = getAnalytics(fb);
  }
  return analytics;
}

/** Fire-and-forget event tracking; silently no-ops when analytics is off. */
export function track(event: string, params?: Record<string, string | number>) {
  if (analytics) logEvent(analytics, event, params);
}
