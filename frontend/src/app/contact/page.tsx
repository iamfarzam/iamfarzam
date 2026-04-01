import type { Metadata } from "next";

import ContactSection from "@/components/sections/ContactSection";

export const metadata: Metadata = {
  title: "Contact",
  description: "Get in touch — I'd love to hear from you.",
};

export default function ContactPage() {
  return (
    <div className="py-10">
      <ContactSection />
    </div>
  );
}
