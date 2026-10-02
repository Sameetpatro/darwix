from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class IndonesianAccountContext(BaseModel):
    """Tracks consumer finance account context during an installment service call."""
    contract_number: Optional[str] = Field("DWX-ID-98234", description="Nomor kontrak pembiayaan")
    customer_name: Optional[str] = Field("Budi Santoso", description="Nama debitur")
    product_type: str = Field("Sepeda Motor Honda Vario 160", description="Objek pembiayaan")
    monthly_installment: float = Field(850000.0, description="Nominal angsuran per bulan dalam IDR")
    due_date_day: int = Field(10, description="Tanggal jatuh tempo setiap bulan (e.g. tgl 10)")
    tenor_months: int = Field(24, description="Total jangka waktu pembiayaan")
    remaining_tenor: int = Field(14, description="Sisa angsuran bulan")
    overdue_days: int = Field(0, description="Jumlah hari keterlambatan saat ini")
    estimated_denda: float = Field(0.0, description="Akumulasi denda keterlambatan (0.5%/hari setelah grace period)")
    support_path_offered: Optional[str] = Field(None, description="PTP, Waiver, atau Restrukturisasi")

    def calculate_denda(self, days_late: int) -> float:
        """
        Calculates denda based on official policy:
        First 3 days are grace period (0 denda).
        After day 3, 0.5% per day on the monthly installment.
        """
        self.overdue_days = days_late
        if days_late <= 3:
            self.estimated_denda = 0.0
        else:
            billable_days = days_late - 3
            self.estimated_denda = billable_days * 0.005 * self.monthly_installment
        return self.estimated_denda
