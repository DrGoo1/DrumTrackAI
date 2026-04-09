def rank_by_drummer_similarity(candidates, profile):

    def score(c):
        s = 0

        fam = c.get("family")
        if fam in profile.get("preferredGrooveFamilies", []):
            s += 0.4

        if profile.get("timeFeel") == c.get("feel"):
            s += 0.2

        complexity = abs(c.get("density",0.5) - profile.get("targetDensity",0.5))
        s += (1 - complexity)

        return s

    return sorted(candidates, key=score, reverse=True)
