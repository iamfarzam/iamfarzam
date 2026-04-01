# API Reference

Base URL: `/api/v1/`

All endpoints return JSON. All GET endpoints filter by `is_active=True` and order by the `order` field.

## Profile

### `GET /api/v1/profile/`

Returns the singleton profile. Returns `{}` if no profile exists.

**Response:**

```json
{
  "full_name": "Farzam Mehdi",
  "headline": "Backend Developer | ML Enthusiast",
  "bio": "Backend developer focused on Python...",
  "avatar": "/media/profile/avatar.jpg",
  "resume": "/media/profile/resume.pdf",
  "email": "contact@example.com",
  "location": "Earth",
  "github_url": "https://github.com/iamfarzam",
  "linkedin_url": "https://linkedin.com/in/example",
  "twitter_url": "",
  "website_url": "",
  "meta_title": "Farzam Mehdi - Portfolio",
  "meta_description": "Backend developer portfolio",
  "og_image": "/media/profile/og.jpg"
}
```

## Skills

### `GET /api/v1/skills/`

Returns skill categories with nested skills.

**Response:**

```json
[
  {
    "id": 1,
    "name": "Backend",
    "skills": [
      { "id": 1, "name": "Python", "icon": "python", "proficiency": 90 },
      { "id": 2, "name": "Django", "icon": "django", "proficiency": 85 }
    ]
  }
]
```

## Projects

### `GET /api/v1/projects/`

Returns all active projects.

**Response:**

```json
[
  {
    "title": "Sample CV Project",
    "slug": "sample-cv-project",
    "summary": "Real-time facial expression detection pipeline",
    "thumbnail": "/media/projects/emotion.jpg",
    "technologies": [
      { "name": "Python", "icon": "python" },
      { "name": "OpenCV", "icon": "opencv" }
    ],
    "github_url": "https://github.com/iamfarzam/sample-cv-project",
    "live_url": "",
    "is_featured": true
  }
]
```

### `GET /api/v1/projects/{slug}/`

Returns a single project by slug with full description.

**Response:**

```json
{
  "title": "Sample CV Project",
  "slug": "sample-cv-project",
  "summary": "Real-time facial expression detection pipeline",
  "description": "Full markdown description of the project...",
  "thumbnail": "/media/projects/emotion.jpg",
  "image": "/media/projects/emotion-detail.jpg",
  "technologies": [
    { "name": "Python", "icon": "python" }
  ],
  "github_url": "https://github.com/iamfarzam/sample-cv-project",
  "live_url": "",
  "is_featured": true,
  "created_at": "2026-01-15T10:30:00Z"
}
```

## Experience

### `GET /api/v1/experience/`

Returns work experience entries. `end_date` is `null` for current positions.

**Response:**

```json
[
  {
    "id": 1,
    "company": "Example Corp",
    "role": "Backend Developer",
    "location": "Remote",
    "start_date": "2023-01-01",
    "end_date": null,
    "description": "Building APIs and services...",
    "company_url": "https://example.com",
    "company_logo": "/media/experience/example.png"
  }
]
```

## Education

### `GET /api/v1/education/`

Returns education entries.

**Response:**

```json
[
  {
    "id": 1,
    "institution": "University",
    "degree": "BS Computer Science",
    "field_of_study": "Computer Science",
    "start_date": "2019-01-01",
    "end_date": "2023-01-01",
    "description": "",
    "institution_logo": "/media/education/uni.png"
  }
]
```

## Contact

### `POST /api/v1/contact/`

Submits a contact form message. Rate-limited to **5 requests per hour**.

**Request:**

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Project Inquiry",
  "message": "I'd like to discuss a project..."
}
```

**Response (201):**

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Project Inquiry",
  "message": "I'd like to discuss a project..."
}
```

**Response (429 — Rate Limited):**

```json
{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

**Response (400 — Validation Error):**

```json
{
  "email": ["Enter a valid email address."],
  "message": ["This field may not be blank."]
}
```
