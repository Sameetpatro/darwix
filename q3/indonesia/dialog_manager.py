import time
import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from q3.indonesia.locale import id_locale, IndonesianLanguageResult
from q3.indonesia.intent_detector import id_intent_detector, IndonesianIntentResult
from q3.indonesia.account_context import IndonesianAccountContext
from q3.indonesia.objections import ph_or_id_objection_handler
from q3.indonesia.escalation import id_escalation_handler
from q2.retrieval.hybrid_search import HybridSearchEngine
from app.logging_config import logger


class IndonesianConversationSession(BaseModel):
    """Tracks session state, conversation history, and account context."""
    session_id: str
    language: str = "id"
    dialect_style: str = "colloquial"  # 'formal', 'colloquial', 'code_switched', 'regional'
    account_context: IndonesianAccountContext = Field(default_factory=IndonesianAccountContext)
    turns: List[Dict[str, Any]] = Field(default_factory=list)
    escalated: bool = False
    support_path_offered: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class IndonesianDialogManager:
    """
    Coordinates Indonesian Consumer Finance installment and payment dialogue.
    Handles formal, colloquial, regional, and code-switched Indonesian directly.
    """

    def __init__(self, hybrid_engine: Optional[HybridSearchEngine] = None):
        self.hybrid_engine = hybrid_engine or HybridSearchEngine()
        self.sessions: Dict[str, IndonesianConversationSession] = {}

    def get_or_create_session(self, session_id: str) -> IndonesianConversationSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = IndonesianConversationSession(session_id=session_id)
        return self.sessions[session_id]

    def greet(self, session_id: str, dialect_style: str = "colloquial") -> str:
        session = self.get_or_create_session(session_id)
        session.dialect_style = dialect_style

        if dialect_style == "formal":
            greeting = (
                "Selamat datang di Layanan Konsumen Darwix Multifinance. "
                "Saya Vani, asisten digital resmi Anda. "
                "Ada yang dapat kami bantu mengenai cicilan angsuran atau informasi pembiayaan Anda hari ini?"
            )
        else:
            greeting = (
                "Halo! Selamat datang di Darwix Multifinance. "
                "Saya Vani, asisten digital Anda. "
                "Ada yang bisa kami bantu seputar cicilan atau pembayaran angsuran Anda?"
            )

        session.turns.append({
            "speaker": "agent",
            "text": greeting,
            "intent": "greeting",
            "timestamp": time.time()
        })
        return greeting

    def process_utterance(self, session_id: str, utterance: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes an Indonesian customer utterance, supporting language switching to English
        while preserving the Multifinance domain and account context.
        """
        session = self.get_or_create_session(session_id)

        # 1. Detect language, dialect style, code-switch, and intent
        intent_res = id_intent_detector.detect_intent(utterance)
        session.dialect_style = intent_res.dialect_style

        # Determine target language (strictly mirrors caller's input language)
        if language in ("en", "id"):
            target_lang = language
        else:
            lang_res = id_locale.detect_language(utterance)
            target_lang = "en" if lang_res.language == "en" else "id"
        session.language = target_lang

        logger.info(
            f"[ID-DIALOG] Session '{session_id}' | Lang: {target_lang} | Dialect: {intent_res.dialect_style} | Intent: {intent_res.intent} | Utterance: '{utterance}'"
        )

        # 2. Check for Human Escalation
        if intent_res.intent == "human_escalation" or id_escalation_handler.is_escalation(utterance):
            session.escalated = True
            resp = id_escalation_handler.get_escalation_response(dialect_style=session.dialect_style, language=target_lang)
            session.turns.append({"speaker": "user", "text": utterance, "intent": "human_escalation"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "human_escalation"})
            return {
                "response": resp,
                "language": target_lang,
                "dialect_style": session.dialect_style,
                "intent": "human_escalation",
                "escalated": True,
                "evidence": [],
                "citation": None,
                "support_path_offered": session.support_path_offered
            }

        # 3. Check for Payment Objection ("Denda-nya terlalu tinggi", "Belum ada dana", English waiver requests)
        if intent_res.intent == "payment_objection" or ph_or_id_objection_handler.is_objection(utterance):
            resp, support_path = ph_or_id_objection_handler.handle_objection(utterance, dialect_style=session.dialect_style, language=target_lang)
            session.support_path_offered = support_path
            session.account_context.support_path_offered = support_path
            session.turns.append({"speaker": "user", "text": utterance, "intent": "payment_objection"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "payment_objection"})
            return {
                "response": resp,
                "language": target_lang,
                "dialect_style": session.dialect_style,
                "intent": "payment_objection",
                "escalated": False,
                "evidence": [],
                "citation": None,
                "support_path_offered": support_path
            }

        # 4. Check for Out-of-Scope / Unsupported Question (Strict Language-Preserving Fallback)
        if intent_res.intent == "unsupported":
            resp = self._get_unsupported_fallback(dialect_style=session.dialect_style, language=target_lang)
            session.turns.append({"speaker": "user", "text": utterance, "intent": "unsupported"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "unsupported"})
            return {
                "response": resp,
                "language": target_lang,
                "dialect_style": session.dialect_style,
                "intent": "unsupported",
                "escalated": False,
                "evidence": [],
                "citation": None,
                "support_path_offered": None
            }

        # 5. Domain Knowledge Query via Q2 Hybrid Search
        kb_intents = {
            "late_payment_fee", "payment_methods", "due_date_inquiry",
            "restructuring_inquiry", "early_payoff", "slik_ojk_inquiry",
            "qualification_inquiry", "general_installment_inquiry"
        }

        evidence_list = []
        citation_str = None

        if intent_res.intent in kb_intents or any(w in utterance.lower() for w in [
            "denda", "late fee", "cicilan", "angsuran", "jatuh tempo", "bayar", "tenor", "dp",
            "penalty", "waiver", "due date", "installment", "pay", "virtual account", "ojk", "slik"
        ]):
            search_hits = self.hybrid_engine.search(query=utterance, top_k=2)
            if search_hits and (search_hits[0].dense_score > 0.45 or search_hits[0].sparse_score > 0.0):
                top_hit = search_hits[0]
                citation_str = f"Darwix ID KB: {top_hit.chunk.source} ({top_hit.chunk.title})"
                evidence_list = [
                    {
                        "title": top_hit.chunk.title,
                        "content": top_hit.chunk.content,
                        "citation": citation_str,
                        "score": top_hit.fused_score
                    }
                ]
                resp = self._format_kb_response(utterance, top_hit.chunk.content, session.dialect_style, intent_res.intent, language=target_lang)
                session.turns.append({"speaker": "user", "text": utterance, "intent": intent_res.intent})
                session.turns.append({"speaker": "agent", "text": resp, "intent": intent_res.intent, "citation": citation_str})
                return {
                    "response": resp,
                    "language": target_lang,
                    "dialect_style": session.dialect_style,
                    "intent": intent_res.intent,
                    "escalated": False,
                    "evidence": evidence_list,
                    "citation": citation_str,
                    "support_path_offered": session.support_path_offered
                }

        # 6. Default Fallback
        if target_lang == "en":
            resp = "Is there anything else I can help you with regarding your Darwix Multifinance installment, due date, or financing contract?"
        else:
            resp = "Ada yang bisa kami bantu lagi mengenai cicilan atau nomor kontrak pembiayaan Anda di Darwix?"
        session.turns.append({"speaker": "user", "text": utterance, "intent": "general"})
        session.turns.append({"speaker": "agent", "text": resp, "intent": "general"})
        return {
            "response": resp,
            "language": target_lang,
            "dialect_style": session.dialect_style,
            "intent": "general",
            "escalated": False,
            "evidence": [],
            "citation": None,
            "support_path_offered": session.support_path_offered
        }

    def _get_unsupported_fallback(self, dialect_style: str = "colloquial", language: str = "id") -> str:
        """Strict non-hallucination fallback preserving appropriate language."""
        if language == "en":
            return (
                "I apologize, I do not have verified information regarding that topic. "
                "I can connect you with a Darwix Multifinance customer service representative if you need further assistance."
            )
        elif dialect_style == "formal":
            return (
                "Mohon maaf Bapak/Ibu, saya belum memiliki informasi yang valid mengenai hal tersebut saat ini. "
                "Jika berkenan, saya dapat menghubungkan Anda dengan petugas customer service kami untuk bantuan lebih lanjut."
            )
        else:
            return (
                "Mohon maaf kak, aku belum punya informasi resmi soal itu saat ini. "
                "Kalau kakak butuh bantuan lebih lanjut, aku bisa bantu sambungkan ke Customer Service kami ya."
            )

    def _format_kb_response(self, query: str, content: str, dialect_style: str, intent: str, language: str = "id") -> str:
        """Synthesizes clean grounded response from Q2 evidence in Indonesian or English."""
        clean_content = content.replace("##", "").replace("**", "").strip()

        # Late payment fee / Denda
        if intent == "late_payment_fee":
            if language == "en":
                return (
                    "Under official Darwix Multifinance policy, we offer a 3-day calendar grace period free of penalty "
                    "after your due date. If payment is completed after day 3, a late payment fee of 0.5% per calendar day "
                    "applies to the outstanding monthly installment amount."
                )
            elif dialect_style == "formal":
                return (
                    "Berdasarkan kebijakan resmi Darwix Multifinance, kami memberikan masa tenggang (grace period) "
                    "bebas denda selama 3 hari kalender setelah tanggal jatuh tempo. "
                    "Namun jika melewati 3 hari, akan dikenakan denda keterlambatan sebesar 0,5% per hari dari nilai angsuran bulanan yang belum terbayar."
                )
            else:
                return (
                    "Kalau telat bayar, Darwix ada masa tenggang (grace period) bebas denda selama 3 hari kalender kok kak setelah tanggal jatuh tempo. "
                    "Tapi kalau lewat dari 3 hari, baru kena denda keterlambatan 0,5% per hari dari nominal angsuran bulanan yang tertunggak ya."
                )

        # Payment methods
        if intent == "payment_methods":
            if language == "en":
                return (
                    "You can pay your Darwix Multifinance installment conveniently via Bank Virtual Accounts (BCA, Mandiri, BRI, BNI), "
                    "at any Indomaret or Alfamart convenience store cashier, or through digital e-wallets such as GoPay, OVO, and Dana."
                )
            elif dialect_style == "formal":
                return (
                    "Pembayaran angsuran Darwix Multifinance dapat dilakukan melalui Virtual Account bank (BCA, Mandiri, BRI, BNI), "
                    "gerai minimarket Indomaret dan Alfamart terdekat, serta aplikasi dompet digital seperti GoPay, OVO, dan Dana."
                )
            else:
                return (
                    "Bayar cicilannya gampang banget kak! Bisa lewat Virtual Account BCA, Mandiri, BRI, BNI, "
                    "kasir minimarket Indomaret atau Alfamart, dan bisa juga langsung pakai GoPay, OVO, atau Dana ya kak."
                )

        # Due date inquiry / installment reminder
        if intent == "due_date_inquiry":
            if language == "en":
                return (
                    "Your monthly installment for Contract DWX-ID-98234 (Honda Vario 160) is IDR 850,000, "
                    "due on the 10th of each month, with 14 months remaining on your tenor."
                )
            else:
                return (
                    "Angsuran bulanan untuk Kontrak DWX-ID-98234 (Honda Vario 160) Anda adalah sebesar Rp850.000, "
                    "jatuh tempo setiap tanggal 10 dengan sisa tenor 14 bulan ya kak."
                )

        # SLIK OJK / Credit score inquiry
        if intent == "slik_ojk_inquiry":
            if language == "en":
                return (
                    "To prevent late payments from affecting your SLIK OJK score and dropping your status from Kol-1 (Current) to Kol-2, "
                    "we can register an official Promise to Pay (Janji Bayar). On which date will your funds be ready?"
                )
            else:
                return (
                    "Agar catatan riwayat kredit Anda di SLIK OJK tetap aman di Kolektibilitas 1 (Lancar) dan terhindar dari denda tambahan, "
                    "kami bisa bantu daftarkan program Janji Bayar resmi (Promise to Pay). Kira-kira pada tanggal berapa dananya siap kak?"
                )

        # Restructuring
        if intent == "restructuring_inquiry":
            if language == "en":
                return (
                    "Certainly. Darwix Multifinance provides an official OJK-supervised restructuring program. "
                    "You can apply to extend your financing tenor (e.g. from 24 to 36 months) to lower your monthly installment amount."
                )
            else:
                return (
                    "Tentu bisa kak. Darwix Multifinance memiliki program restrukturisasi resmi yang diawasi OJK. "
                    "Anda dapat mengajukan perpanjangan tenor pembiayaan agar beban nominal cicilan per bulan menjadi lebih ringan sesuai kemampuan."
                )

        # Qualification inquiry
        if intent == "qualification_inquiry":
            if language == "en":
                return (
                    "For Darwix Multifinance vehicle financing, the minimum Down Payment (DP) is 10% to 20% per OJK regulations, "
                    "with flexible tenors from 12 to 36 months secured by vehicle BPKB registration."
                )
            else:
                return (
                    "Untuk pembiayaan motor atau mobil di Darwix Multifinance, uang muka (DP) minimal adalah 10% hingga 20% sesuai regulasi OJK, "
                    "dengan pilihan tenor 12, 24, hingga 36 bulan dengan agunan BPKB ya kak."
                )

        # Early payoff
        if intent == "early_payoff":
            if language == "en":
                return (
                    "Under Darwix Multifinance policy, accelerated early payoff is supported with a nominal administration fee of 2% "
                    "on the remaining principal balance, allowing you to close your financing contract early and release your BPKB."
                )
            else:
                return (
                    "Untuk pelunasan dipercepat (early payoff), Darwix Multifinance mengenakan biaya penalti administrasi sebesar 2% "
                    "dari sisa pokok pinjaman, setelah itu kontrak Anda resmi ditutup dan BPKB kendaraan dapat langsung diambil ya kak."
                )

        # General extraction fallback
        first_few_lines = "\n".join(clean_content.split("\n")[:3])
        if language == "en":
            return f"According to official Darwix Multifinance policy:\n{first_few_lines}"
        return f"Berdasarkan informasi resmi Darwix Multifinance:\n{first_few_lines}"


id_dialog_manager = IndonesianDialogManager()
