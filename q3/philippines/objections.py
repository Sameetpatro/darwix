import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PhilippinesObjectionHandler:
    """
    Handles culturally grounded insurance objections in the customer's native
    tongue (Taglish, Filipino, or English) without breaking rapport.
    """

    def is_objection(self, text: str) -> bool:
        clean = text.lower().strip()
        patterns = [
            r"\b(?:mahal|masyadong\s+mahal|sobrang\s+mahal|expensive|pricey|costly)\b",
            r"\b(?:wala\s+pa|walang)\b.*\b(?:pera|budget|cash|ipon)\b",
            r"\b(?:cannot\s+afford|can't\s+afford|tight\s+budget|no\s+budget)\b",
            r"\b(?:malugi|malulugi|scam|baka\s+scam|hindi\s+mabayaran|baka\s+mawala)\b",
            r"\b(?:next\s+time|sa\s+susunod|matagal\s+pa\s+naman|bata\s+pa\s+ako)\b"
        ]
        return any(bool(re.search(p, clean)) for p in patterns)

    def handle_objection(self, text: str, language: str = "taglish") -> str:
        clean = text.lower().strip()

        # 1. Price / Expensive objection
        if any(w in clean for w in ["mahal", "expensive", "pricey", "costly"]):
            if language == "fil":
                return (
                    "Nauunawaan ko po kayo. Ngunit sa Darwix po, maaari nating i-adjust ang plano batay sa inyong kakayahan. "
                    "Mayroon po tayong SecureTerm na nagsisimula lamang sa humigit-kumulang ₱1,500 kada buwan o ₱50 lamang bawat araw—"
                    "kasing halaga lamang ng isang kape o meryenda. Nais niyo po bang gawan natin ito ng quotation na abot-kaya?"
                )
            elif language == "en":
                return (
                    "I completely understand your concern. The great thing with Darwix is that we customize the policy to your specific budget. "
                    "Our SecureTerm plan starts at around ₱1,500 per month—just about ₱50 a day, which is the cost of a daily cup of coffee or snack. "
                    "Would you like us to customize a quotation that comfortably fits your budget?"
                )
            else: # taglish
                return (
                    "Naiintindihan ko po kayo. Pero ang kagandahan po sa Darwix, pwede po nating i-customize ang plan para swak sa inyong budget. "
                    "Meron po tayong SecureTerm na nagsisimula lamang sa humigit-kumulang ₱1,500 kada buwan—o ₱50 lang bawat araw, kasing halaga lang ng isang kape o merienda. "
                    "Gusto niyo po bang gawan natin ng quotation na pasok sa inyong buwanang budget?"
                )

        # 2. Trust / Scam / Loss objection
        if any(w in clean for w in ["malugi", "scam", "hindi mabayaran", "mawala"]):
            if language == "fil":
                return (
                    "Nirerespeto ko po ang inyong pag-iingat. Ang Darwix Life po ay 100% lisensyado at pinangangasiwaan ng Insurance Commission ng Pilipinas. "
                    "Bukod dito, opisyal po nating partner ang mga pinagkakatiwalaang bangko tulad ng BDO, BPI, at Metrobank. "
                    "Lahat po ng benepisyo ay nakasaad sa legal na kontrata upang sigurado ang proteksyon ng inyong pamilya."
                )
            elif language == "en":
                return (
                    "I completely respect your caution. Darwix Life is fully licensed and strictly regulated by the Insurance Commission of the Philippines. "
                    "Furthermore, we are official bancassurance partners with top Philippine banks like BDO, BPI, and Metrobank. "
                    "Every single peso of death benefit and cash value is legally secured by strict capital reserve requirements."
                )
            else: # taglish
                return (
                    "Naiintindihan ko po ang inyong pag-iingat. Ang Darwix Life po ay 100% lisensyado at mahigpit na pinangangasiwaan ng Insurance Commission ng Pilipinas. "
                    "Bukod dito, partner po namin ang mga nangungunang bangko sa bansa tulad ng BDO, BPI, at Metrobank. "
                    "Lahat po ng benepisyo at coverage ay nakasulat sa legal na kontrata upang sigurado ang proteksyon ng inyong pamilya."
                )

        # 3. Postponing / No budget today
        if language == "fil":
            return (
                "Opo, nauunawaan ko po. Ngunit habang mas bata at malusog pa tayo, doon pinakamura ang premium ng life insurance. "
                "Kapag naghintay po tayo, maaaring magmahal ang rate dulot ng edad. "
                "Maaari po tayong magsimula sa pinakamababang antas ng proteksyon muna habang kayo ay nag-iipon."
            )
        elif language == "en":
            return (
                "I understand completely. However, securing a policy while you are young and in good health locks in the lowest possible premium for the entire term. "
                "Waiting often means higher premiums due to age or unforeseen health changes. We can start with a basic affordable protection plan today."
            )
        else: # taglish
            return (
                "Opo, nauunawaan ko po. Pero alam niyo po ba na habang mas bata at malusog pa tayo, doon pinakamura ang premium ng life insurance? "
                "Kapag naghintay po tayo, baka magmahal ang rate dahil sa edad. Pwede po tayong magsimula sa pinakamababang coverage muna habang nag-iipon."
            )


ph_objection_handler = PhilippinesObjectionHandler()
