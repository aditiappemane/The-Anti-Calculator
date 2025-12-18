import re
import logging
import pytesseract
import pdfplumber
from PIL import Image
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class VisionService:
    def __init__(self):
        pass

    def _extract_text_from_image(self, image_path: str) -> str:
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            logger.info(f"Extracted image text preview: {text[:200]}")
            return text
        except Exception as e:
            logger.error("Image OCR failed", exc_info=True)
            raise HTTPException(status_code=500, detail="Image OCR failed")

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            pages = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages.append(page_text)
            text = "\n".join(pages)
            logger.info(f"Extracted PDF text preview: {text[:200]}")
            return text
        except Exception as e:
            logger.error("PDF OCR failed", exc_info=True)
            raise HTTPException(status_code=500, detail="PDF OCR failed")

    def _redact_pii(self, text: str) -> str:
        # IBAN
        text = re.sub(
            r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}",
            "[REDACTED_IBAN]",
            text,
            flags=re.IGNORECASE,
        )

        # Names
        text = re.sub(
            r"(Name|Employee|Client)\s*:\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)*",
            r"\1: [REDACTED_NAME]",
            text,
        )

        # Bank account numbers
        text = re.sub(
            r"(Account|A/C)\s*No\.?\s*\d+",
            r"\1 No: [REDACTED_ACCOUNT]",
            text,
            flags=re.IGNORECASE,
        )

        return text

    def _extract_financial_numbers(self, text: str) -> dict:
        logger.info(f"Processing text for financial numbers:\n{text[:1000]}...")

        def find_value(patterns, text_content):
            # This regex allows for optional currency symbols (AED, DHS) and an optional dot after them.
            # It also ensures the number group is correctly captured.
            number_pattern_suffix = r"(?:[:\s]*(?:AED|DHS)?\.?\s*)?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\b"

            for i, pattern_prefix in enumerate(patterns):
                full_pattern = fr'{pattern_prefix}{number_pattern_suffix}'
                match = re.search(full_pattern, text_content, re.IGNORECASE)
                if match:
                    logger.info(f"Pattern {i+1} matched: '{full_pattern}'. Value: {match.group(1)}")
                    return float(match.group(1).replace(",", ""))
                else:
                    logger.info(f"Pattern {i+1} did not match: '{full_pattern}'")
            return None

        def find_all_allowances(text_content):
            allowances_map = {}
            # Regex to find various allowance types and their amounts
            # The find_value function now handles the currency token.
            allowance_patterns = {
                "housing_allowance": [r"Housing\s*Allowance", r"Housing"],
                "transport_allowance": [r"Transport(?:ation)?\s*Allowance", r"Transport"],
                "other_allowances": [r"Other\s*Allowance", r"Other"],
                "total_allowances": [r"Total\s*Allowance(?:s)?", r"Allowance(?:s)?\s*Total"],
            }

            for key, patterns in allowance_patterns.items():
                value = find_value(patterns, text_content)
                if value is not None:
                    allowances_map[key] = value
            return allowances_map

        basic_salary = find_value([
            r"Basic\s*Salary",
            r"Basic\s*Pay",
            r"Gross\s*Basic",
            r"Basic",
        ], text)
        deductions = find_value([
            r"Total\s*Deduction(?:s)?",
            r"Deduction(?:s)?",
            r"Deduction(?:s)?\s*Total",
        ], text)
        net_salary = find_value([
            r"Net\s*Salary",
            r"Net\s*Pay",
            r"Amount\s*Payable",
            r"Total\s*Net",
            r"Take\s*Home\s*Pay",
            r"Pay\s*after\s*deductions",
            r"Net",
        ], text)
        
        allowances_data = find_all_allowances(text)

        # Fallback calculation for net_salary
        if net_salary is None:
            total_allowances = sum(allowances_data.values()) if allowances_data else 0
            if basic_salary is not None and deductions is not None:
                net_salary = basic_salary + total_allowances - deductions
                logger.info(f"Calculated net_salary fallback: {net_salary} (Basic: {basic_salary}, Allowances: {total_allowances}, Deductions: {deductions})")
            elif basic_salary is not None and total_allowances > 0:
                 # If deductions are not found, assume 0 for fallback if basic_salary and allowances exist
                net_salary = basic_salary + total_allowances
                logger.info(f"Calculated net_salary fallback (no deductions): {net_salary} (Basic: {basic_salary}, Allowances: {total_allowances})")


        return {
            "basic_salary": basic_salary,
            "allowances": allowances_data if allowances_data else {},
            "deductions": deductions,
            "net_salary": net_salary,
        }

    async def extract_financial_data(self, file_path: str, file_type: str) -> dict:
        if file_type.startswith("image/"):
            raw_text = self._extract_text_from_image(file_path)
        elif file_type == "application/pdf":
            raw_text = self._extract_text_from_pdf(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        redacted_text = self._redact_pii(raw_text)
        data = self._extract_financial_numbers(redacted_text)

        return {k: v for k, v in data.items() if v is not None}
