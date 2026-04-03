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

async function fetchAPI<T>(endpoint: string, revalidate = 3600): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    next: { revalidate },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchProfile(): Promise<Profile> {
  return fetchAPI<Profile>("/profile/");
}

export async function fetchSkills(): Promise<SkillCategory[]> {
  try {
    return await fetchAPI<SkillCategory[]>("/skills/");
  } catch {
    return [];
  }
}

export async function fetchProjects(): Promise<ProjectSummary[]> {
  return fetchAPI<ProjectSummary[]>("/projects/");
}

export async function fetchProject(slug: string): Promise<ProjectDetail> {
  return fetchAPI<ProjectDetail>(`/projects/${slug}/`);
}

export async function fetchExperience(): Promise<Experience[]> {
  return fetchAPI<Experience[]>("/experience/");
}

export async function fetchEducation(): Promise<Education[]> {
  return fetchAPI<Education[]>("/education/");
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
