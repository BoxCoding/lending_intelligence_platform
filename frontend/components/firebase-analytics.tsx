"use client";
/** Initialises Firebase Analytics and logs page views on route changes. */
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { initAnalytics, track } from "@/lib/firebase";

export default function FirebaseAnalytics() {
  const pathname = usePathname();

  useEffect(() => {
    initAnalytics();
  }, []);

  useEffect(() => {
    track("page_view", { page_path: pathname });
  }, [pathname]);

  return null;
}
