from data.repos.voice_profiles import VoiceProfilesRepo
from core.agents.v2.agent1_voice import run_agent1 as run_agent1_v2

async def refine_voice_profile(
    profile_id: str,
    audio_profile: dict = None,
    transcript_meta: dict = None,
    modalities: list = None
):
    print("🔥 [REFINE] START profile_id =", profile_id)

    parent_profile = await VoiceProfilesRepo.get_human_profile_raw(profile_id)

    if not parent_profile:
        raise RuntimeError("Parent profile not found")

    print("🔥 [REFINE] parent_profile keys =", parent_profile.keys())

    v2_output = await run_agent1_v2(parent_profile=parent_profile)

    print("🔥 [REFINE] V2 OUTPUT KEYS =", v2_output.keys())

    # Inject Multimodal Data into V2 Output for Persistence
    if audio_profile:
        v2_output["audio_profile"] = audio_profile
    if transcript_meta:
        v2_output["transcript_meta"] = transcript_meta
    if modalities:
        v2_output["modalities"] = modalities

    await VoiceProfilesRepo.save_profile_v2(
        brand_id=parent_profile["brand_id"],
        parent_profile_id=profile_id,
        agent1_v2_output=v2_output
    )

    print("✅ [REFINE] V2 SAVE COMPLETE")
    return v2_output
