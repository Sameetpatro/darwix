import re
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class IndonesianObjectionHandler:
    """
    Handles payment objections in Indonesian Consumer Finance:
    - High late fee / denda ("Denda-nya terlalu tinggi")
    - Financial hardship / delay ("Belum ada uang / lagi seret")
    """

    def is_objection(self, text: str) -> bool:
        clean = text.lower().strip()
        patterns = [
            r"\b(?:denda.*(?:terlalu\s*tinggi|kemahalan|mahal|berat|tinggi\s*banget|kebanyakan))\b",
            r"\b(?:belum\s*ada\s*(?:dana|uang|duit)|lagi\s*seret|gajian\s*belum\s*cair|nggak\s*ada\s*duit)\b",
            r"\b(?:bisa\s*minta\s*(?:keringanan\s*denda|potongan\s*denda|hapus\s*denda))\b",
            r"\b(?:waive\s*(?:the\s*)?(?:late\s*)?(?:fee|penalty|denda)|fee.*(?:too\s*high|expensive)|waiver|discount\s*(?:on\s*)?(?:late\s*)?(?:fee|denda)|cancel\s*penalty)\b",
            r"\b(?:tight\s*budget|no\s*funds|salary\s*delayed|hardship|can't\s*afford\s*(?:the\s*)?(?:fee|penalty|payment))\b"
        ]
        return any(bool(re.search(p, clean)) for p in patterns)

    def handle_objection(self, text: str, dialect_style: str = "colloquial", language: str = "id") -> Tuple[str, str]:
        """
        Returns (response_text, support_path_offered)
        """
        clean = text.lower().strip()

        # 1. High late fee objection -> Offer Denda Waiver on same-day payment
        if any(w in clean for w in ["denda", "tinggi", "kemahalan", "mahal", "potongan", "fee", "penalty", "waive", "waiver"]):
            if language == "en":
                resp = (
                    "I completely understand your concern. The 0.5% daily fee follows standard OJK regulations. "
                    "However, if you settle the principal installment payment today, we can recommend a 100% late fee waiver (denda waiver) "
                    "program so you only pay the principal amount. Would you like me to process this waiver for you now?"
                )
            elif dialect_style == "formal":
                resp = (
                    "Saya memahami kendala yang Bapak/Ibu rasakan. Besaran denda 0,5% per hari merupakan ketentuan standar asosiasi dan regulasi OJK. "
                    "Namun untuk membantu Bapak/Ibu hari ini, apabila pembayaran pokok angsuran diselesaikan pada hari ini, "
                    "kami dapat memberikan rekomendasi program penghapusan denda (denda waiver) hingga 100% sehingga Anda cukup membayar pokok cicilan saja. "
                    "Apakah bersedia kami bantu proseskan sekarang?"
                )
            else:
                resp = (
                    "Saya paham banget kendala yang kakak rasakan. Besaran denda 0,5% per hari ini memang standar resmi OJK. "
                    "Tapi jangan khawatir, kabar baiknya kalau kakak bisa selesaikan pokok angsurannya hari ini, "
                    "kami bisa bantu ajukan program penghapusan denda (denda waiver) sampai 100% jadi kakak cukup bayar pokok cicilannya aja! "
                    "Gimana kak, mau dibantu proses sekarang?"
                )
            return resp, "Denda Waiver Request"

        # 2. Financial hardship / cash delay -> Offer Promise to Pay (PTP)
        if language == "en":
            resp = (
                "We completely understand that financial circumstances can be difficult. "
                "To keep your credit record safe in SLIK OJK and stop further late penalties from accumulating, "
                "we can register an official Promise to Pay (PTP) in our system. "
                "On which date will your funds be ready so we can record it?"
            )
        elif dialect_style == "formal":
            resp = (
                "Baik Bapak/Ibu, kami sangat mengerti situasi ekonomi yang terkadang tidak menentu. "
                "Agar catatan skor kredit Anda di SLIK OJK tetap aman dan terhindar dari denda yang terus bertambah, "
                "kami dapat membantu mendaftarkan program Janji Bayar resmi (Promise to Pay). "
                "Kira-kira pada tanggal berapa dana Bapak/Ibu akan siap masuk, agar dapat kami catat dalam sistem?"
            )
        else:
            resp = (
                "Oke kak, kami sangat ngerti kondisi keuangan yang lagi seret. "
                "Biar riwayat kredit kakak di SLIK OJK tetap aman dan denda nggak makin bengkak, "
                "kami bisa bantu daftarin program Janji Bayar resmi (Promise to Pay). "
                "Kira-kira tanggal berapa dananya ready kak, biar kami bantu jadwalkan di sistem?"
            )
        return resp, "Promise to Pay (PTP)"


ph_or_id_objection_handler = IndonesianObjectionHandler()
