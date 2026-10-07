from app.discovery.engine import RequirementDiscoveryEngine

PROMPT = (
    "Buatkan website portfolio profesional untuk Data Engineering dengan target utama recruiter, HR, "
    "perusahaan teknologi, dan calon client yang membutuhkan jasa Data Engineer. Tujuan website adalah "
    "untuk menampilkan profil profesional, pengalaman, skill, sertifikasi, dan project agar mempermudah "
    "proses mencari kerja sekaligus mendapatkan calon client. Gunakan gaya visual modern, minimalist, "
    "clean, professional, dan dark theme. Section wajib meliputi Hero, About, Skills, Experience, "
    "Projects, Certifications, dan Contact. Untuk bagian Contact, gunakan contact form yang mengirim "
    "data ke email dengan field wajib Name, Email, Company, dan Message. Gunakan website referensi yang "
    "saya berikan hanya sebagai inspirasi untuk layout, animation, dan typography tanpa menyalin desain "
    "secara langsung. Deployment platform tidak perlu saya tentukan dan boleh menjadi keputusan teknis internal."
)

def test_final_prompt_extracts_portfolio_focus():
    result = RequirementDiscoveryEngine().analyze(PROMPT)
    data = {x.key: x.value for x in result.confirmed}
    assert data["portfolio_focus"] == "Data Engineering"

def test_final_prompt_extracts_both_project_goals():
    result = RequirementDiscoveryEngine().analyze(PROMPT)
    data = {x.key: x.value for x in result.confirmed}
    assert data["project_goal"] == ["job_search", "client_acquisition"]
