"""
Verification script for AI Detection & Humanizer accuracy enhancements.
"""
import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.ai_detection import analyze_ai_generated
from app.services.paraphraser import paraphrase_text

# Sample 1: Typical AI-generated essay text (uniform sentence lengths, AI connectives, zero typos)
AI_SAMPLE = (
    "Furthermore, artificial intelligence plays a crucial role in modern technological evolution. "
    "Moreover, it is essential to consider how machine learning models delve into vast datasets to extract patterns. "
    "Consequently, these algorithms foster innovation across various industries, creating a tapestry of opportunity. "
    "In conclusion, the transformative power of AI serves as a testament to human ingenuity, ensuring a vibrant future."
)

# Sample 2: Typical Human-written text (varying sentence lengths, typos, informal phrasing)
HUMAN_SAMPLE = (
    "I was working on my project late last night and noticed something pretty wierd with the results. "
    "Honestly, I didn't expect it to behave like this at all! "
    "The code kept throwing a minor syntax erro near line 42, but after fixing that quick mistake, everything ran fine. "
    "So anyway, we should probably double-check the raw dataset tomorrow morning before submitting."
)


def run_verification():
    print("==================================================")
    print("      ScholarShield Enhancement Verification      ")
    print("==================================================")

    print("\n[1] Testing AI Sample Text...")
    ai_res = analyze_ai_generated(AI_SAMPLE, include_sentence_breakdown=True)
    print(f" -> AI Probability: {ai_res['ai_probability']}%")
    print(f" -> Most Likely Origin: {ai_res['detector_3_family_classifier']['most_likely_family']}")
    print(f" -> Signals: {ai_res['signals']}")

    print("\n[2] Testing Human Sample Text...")
    human_res = analyze_ai_generated(HUMAN_SAMPLE, include_sentence_breakdown=True)
    print(f" -> AI Probability: {human_res['ai_probability']}%")
    print(f" -> Most Likely Origin: {human_res['detector_3_family_classifier']['most_likely_family']}")
    print(f" -> Signals: {human_res['signals']}")

    print("\n[3] Testing Humanizer Engine on AI Sample...")
    humanized = paraphrase_text(AI_SAMPLE, mode="academic")
    print(f" -> Original Fact Preserved: {humanized['fact_preservation']['preserved']}")
    print(f" -> Rewritten Text: \"{humanized['rewritten_text']}\"")
    
    post_humanize_res = analyze_ai_generated(humanized['rewritten_text'])
    print(f" -> Post-Humanizer AI Probability: {post_humanize_res['ai_probability']}%")
    delta = round(ai_res['ai_probability'] - post_humanize_res['ai_probability'], 1)
    print(f" -> AI Score Reduction Delta: -{delta}%")

    # Assertions for pass/fail
    assert ai_res['ai_probability'] >= 75.0, f"AI sample score too low: {ai_res['ai_probability']}%"
    assert human_res['ai_probability'] <= 25.0, f"Human sample score too high: {human_res['ai_probability']}%"
    assert humanized['fact_preservation']['preserved'] == True, "Fact preservation check failed!"
    assert post_humanize_res['ai_probability'] < ai_res['ai_probability'], "Humanizer failed to reduce AI score!"

    print("\n[SUCCESS] ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()
