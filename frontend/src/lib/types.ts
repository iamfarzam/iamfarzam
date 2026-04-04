export interface Profile {
  full_name: string;
  headline: string;
  tagline: string;
  bio: string;
  avatar: string | null;
  resume: string | null;
  email: string;
  location: string;
  github_url: string;
  linkedin_url: string;
  twitter_url: string;
  website_url: string;
  meta_title: string;
  meta_description: string;
  og_image: string | null;
}

export interface Skill {
  id: number;
  name: string;
  icon: string;
  proficiency: number;
}

export interface SkillCategory {
  id: number;
  name: string;
  skills: Skill[];
}

export interface Technology {
  name: string;
  icon: string;
}

export interface ProjectSummary {
  title: string;
  slug: string;
  summary: string;
  thumbnail: string;
  technologies: Technology[];
  github_url: string;
  live_url: string;
  is_featured: boolean;
}

export interface ProjectDetail extends ProjectSummary {
  description: string;
  image: string | null;
  created_at: string;
}

export interface Experience {
  id: number;
  company: string;
  role: string;
  location: string;
  start_date: string;
  end_date: string | null;
  description: string;
  company_url: string;
  company_logo: string | null;
}

export interface Education {
  id: number;
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string | null;
  description: string;
  institution_logo: string | null;
}
