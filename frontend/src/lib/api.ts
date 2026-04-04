import type {
  Education,
  Experience,
  Profile,
  ProjectDetail,
  ProjectSummary,
  SkillCategory,
} from "./types";

const API_BASE =
  process.env.INTERNAL_API_URL || "http://localhost:8000/api/v1";

// Cache control via env: set to 0 or "no-store" to disable, or seconds to revalidate.
const REVALIDATE_RAW = process.env.NEXT_PUBLIC_REVALIDATE ?? "0";
const cacheOption: RequestInit =
  REVALIDATE_RAW === "no-store" || REVALIDATE_RAW === "0"
    ? { cache: "no-store" }
    : { next: { revalidate: Number(REVALIDATE_RAW) } };

async function fetchAPI<T>(endpoint: string, locale: string = "en"): Promise<T> {
  const langMap: Record<string, string> = { zh: "zh-hans" };
  const acceptLang = langMap[locale] || locale;
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Accept-Language": acceptLang },
    ...cacheOption,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchProfile(locale = "en"): Promise<Profile> {
  return fetchAPI<Profile>("/profile/", locale);
}

export async function fetchSkills(locale = "en"): Promise<SkillCategory[]> {
  try {
    return await fetchAPI<SkillCategory[]>("/skills/", locale);
  } catch {
    return [];
  }
}

export async function fetchProjects(locale = "en"): Promise<ProjectSummary[]> {
  return fetchAPI<ProjectSummary[]>("/projects/", locale);
}

export async function fetchProject(slug: string, locale = "en"): Promise<ProjectDetail> {
  return fetchAPI<ProjectDetail>(`/projects/${slug}/`, locale);
}

export async function fetchExperience(locale = "en"): Promise<Experience[]> {
  return fetchAPI<Experience[]>("/experience/", locale);
}

export async function fetchEducation(locale = "en"): Promise<Education[]> {
  return fetchAPI<Education[]>("/education/", locale);
}

export async function submitContact(data: {
  name: string;
  email: string;
  subject: string;
  message: string;
}): Promise<void> {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const res = await fetch(`${apiUrl}/contact/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to send message");
  }
}
