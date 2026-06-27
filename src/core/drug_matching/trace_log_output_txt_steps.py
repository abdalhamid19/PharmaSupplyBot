"""TXT step writers for different step types."""


class StepWriters:
    """Helper class for writing different step types to TXT."""

    @staticmethod
    def write_brand_lookup(f, row):
        """Write brand lookup step."""
        if row["ai_result"] == "no_hits":
            f.write(
                f"  [brand_lookup] no hits  "
                f"({row['selection_reason']})\n",
            )
        else:
            f.write(
                f"  [brand_lookup] "
                f"{row['candidate_name']}"
                f"  brand={row['candidate_brand']}"
                f"  score={row['score']}\n",
            )

    @staticmethod
    def write_fuzzy(f, row):
        """Write fuzzy search step."""
        if "no candidate" in row.get("selection_reason", ""):
            f.write(
                f"  [fuzzy/{row['scorer']}] "
                f"no hit above threshold={row['threshold']}\n",
            )
        else:
            f.write(
                f"  [fuzzy/{row['scorer']}] "
                f"{row['candidate_name']}"
                f"  brand={row['candidate_brand']}"
                f"  score={row['score']}"
                f"  (threshold={row['threshold']})\n",
            )

    @staticmethod
    def write_final(f, row):
        """Write final match step."""
        ai = row["ai_phase"]
        ai_txt = f"  AI={ai}" if ai != "none" else ""
        f.write(
            f"  >> FINAL: match={row['final_match']}"
            f"  score={row['final_score']}"
            f"  method={row['final_method']}"
            f"{ai_txt}\n",
        )
        f.write(f"     reason: {row['selection_reason']}\n\n")

    @staticmethod
    def write_ai_verify_sent(f, row):
        """Write AI verify sent step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        f.write(
            f"  [AI VERIFY] sent to verify: "
            f"'{row['candidate_name']}'"
            f"  (brand={row['candidate_brand']})"
            f"  score={row['score']} < threshold={row['threshold']}"
            f"{model_txt}\n",
        )

    @staticmethod
    def write_ai_verify_result(f, row):
        """Write AI verify result step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
        f.write(
            f"  [AI VERIFY] result={row['ai_result']}  "
            f"verifying='{row['candidate_name']}'  "
            f"confidence={row['score']}"
            f"{model_txt}{api_txt}\n",
        )
        f.write(f"     {row['selection_reason']}\n")
        if row.get('component_reason'):
            f.write(f"     {row['component_reason']}\n")

    @staticmethod
    def write_ai_search_sent(f, row):
        """Write AI search sent step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        f.write(
            f"  [AI SEARCH] sent with {row['selection_reason']}{model_txt}\n"
        )
        if row.get('candidate_name'):
            f.write(f"     candidates: {row['candidate_name']}\n")

    @staticmethod
    def write_ai_search_result(f, row):
        """Write AI search result step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
        if row["ai_result"] == "ai_found":
            f.write(
                f"  [AI SEARCH] FOUND: "
                f"{row['candidate_name']}"
                f"  confidence={row['score']}"
                f"{model_txt}{api_txt}\n",
            )
        else:
            f.write(
                f"  [AI SEARCH] not found  "
                f"{row['selection_reason']}{api_txt}\n",
            )

    @staticmethod
    def write_ai_review_sent(f, row):
        """Write AI review sent step."""
        first_model_txt = f"  first_model={row['ai_model']}" if row.get('ai_model') else ""
        review_model_txt = f"  review_model={row['ai_review_model']}" if row.get('ai_review_model') else ""
        f.write(
            f"  [AI REVIEW] sent to second model: "
            f"first_decision={row['ai_result']}  "
            f"first_confidence={row['ai_confidence']}"
            f"{first_model_txt}{review_model_txt}\n",
        )
        f.write(f"     {row['selection_reason']}\n")

    @staticmethod
    def write_ai_review_result(f, row):
        """Write AI review result step."""
        review_model_txt = f"  review_model={row['ai_review_model']}" if row.get('ai_review_model') else ""
        api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
        f.write(
            f"  [AI REVIEW] result={row['ai_result']}  "
            f"review_confidence={row['ai_confidence']}"
            f"{review_model_txt}{api_txt}\n",
        )
        f.write(f"     {row['selection_reason']}\n")


__all__ = ["StepWriters"]
