# schema.py: definir la structure json attendue des cv
# et valider les champs et leurs types avec pydantic
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )  # refuser les champs non prevus dans structure attendue


class PersonalInformation(StrictModel):
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    city: str | None
    linkedin: str | None
    github: str | None


class Skills(StrictModel):
    technical_skills: list[str]
    soft_skills: list[str]
    languages: list[str]


class WorkExperience(StrictModel):
    job_title: str | None
    company: str | None
    description: str | None
    technologies: list[str]
    location: str | None
    start_date: str | None
    end_date: str | None


class Education(StrictModel):
    degree: str | None
    school_name: str | None
    start_date: str | None
    is_current: bool | None


class CVData(StrictModel):
    personal_information: PersonalInformation
    professional_summary: str | None
    skills: Skills
    work_experience: list[WorkExperience]
    education: list[Education]
