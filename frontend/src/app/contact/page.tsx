import type { Metadata } from "next";

import ContactSection from "@/components/sections/ContactSection";

export const metadata: Metadata = {
  title: "Contact",
  description: "Get in touch to discuss a project or opportunity.",
};

export default function ContactPage() {
  return (
    <div className="py-10">
      <ContactSection />
    </div>
  );
}
