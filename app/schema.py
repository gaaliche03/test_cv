def champ():
    return {"type": ["string", "null"]}


def objet(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


CVData = objet(
    {
        "personal_information": objet(
            {
                "first_name": champ(),
                "last_name": champ(),
                "email": champ(),
                "phone": champ(),
                "city": champ(),
                "linkedin": champ(),
                "github": champ(),
            }
        ),
        "professional_summary": champ(),
        "skills": objet(
            {
                "technical_skills": {"type": "array", "items": {"type": "string"}},
                "soft_skills": {"type": "array", "items": {"type": "string"}},
                "languages": {"type": "array", "items": {"type": "string"}},
            }
        ),
        "work_experience": {
            "type": "array",
            "items": objet(
                {
                    "job_title": champ(),
                    "company": champ(),
                    "description": champ(),
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "location": champ(),
                    "start_date": champ(),
                    "end_date": champ(),
                }
            ),
        },
        "education": {
            "type": "array",
            "items": objet(
                {
                    "degree": champ(),
                    "school_name": champ(),
                    "start_date": champ(),
                    "is_current": {"type": ["boolean", "null"]},
                }
            ),
        },
    }
)
