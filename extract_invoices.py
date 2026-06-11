import os
import re
import logging
import pandas as pd
import easyocr
from rapidfuzz import fuzz

INPUT_FOLDER = "./data/batch_1/batch_1/batch1_1"
OUTPUT_CSV = "./output/output.csv"
LOG_FILE = "./logs/invoice_extraction.log"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# OCR INITIALIZATION

logger.info("Initializing OCR engine")

reader = easyocr.Reader(
    ["en"],
    gpu=False
)

FIELDS = {
    "seller_name": ["Seller:"], #["seller", "vendor", "supplier", "Seller:"],
    "seller_tax_id":["tax id"], #["tax id", "vat number"],
    "client_name": ["Client:"], #["client", "customer", "bill to", "Client:"],
    "client_tax_id":["client tax id"],
    "invoice_number": ["invoice no", "invoice number"],
    "invoice_date": ["date of issue", "date"],
    "net_worth": ["net worth", "net", "subtotal"],
    "vat": ["vat", "tax"],
    "gross_worth": ["gross worth","gross", "total",]
}


def normalize(txt):
    return txt.lower().strip()


def extract_text(path):

    logger.info(f"OCR started → {path}")

    result = reader.readtext(path)

    rows = []

    for box, text, conf in result:

        x = min(p[0] for p in box)
        y = min(p[1] for p in box)

        rows.append({
            "text": text,
            "x": x,
            "y": y
        })

    rows.sort(
        key=lambda x: x["y"]
    )

    logger.info(
        f"Extracted {len(rows)} text rows"
    )

    return rows


def find_value(field, rows):

    label = None

    for r in rows:

        score = max(
            fuzz.partial_ratio(
                normalize(r["text"]),
                k
            )
            for k in FIELDS[field]
        )

        if score > 80:
            label = r
            break

    if not label:

        logger.warning(
            f"Label not found → {field}"
        )

        return ""

    values = []

    for r in rows:

        if (
            abs(
                r["y"] - label["y"]
            ) < 35
            and
            r["x"] > label["x"]
        ):

            values.append(
                r["text"]
            )

    value = " ".join(values)

    logger.info(
        f"{field} = {value}"
    )

    return value


def clean_money(v):

    m = re.search(
        r"[\d,.]+",
        v
    )

    return m.group() if m else ""


def clean_date(v):

    m = re.search(
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        v
    )

    return m.group() if m else v


def process(path):

    logger.info(
        f"Processing {os.path.basename(path)}"
    )

    rows = extract_text(path)

    output = {
        "file":
            os.path.basename(path),

        "seller_name":
            find_value(
                "seller_name",
                rows
            ),

        "seller_tax_id":
            find_value(
                "seller_tax_id",
                rows
            ),

        "client_name":
            find_value(
                "client_name",
                rows
            ),

        "client_tax_id":
            find_value(
                "client_tax_id",
                rows
            ),

        "invoice_number":
            find_value(
                "invoice_number",
                rows
            ),

        "invoice_date":
            clean_date(
                find_value(
                    "invoice_date",
                    rows
                )
            ),

        "net_worth":
            clean_money(
                find_value(
                    "net_worth",
                    rows
                )
            ),

        "vat":
            clean_money(
                find_value(
                    "vat",
                    rows
                )
            ),

        "gross_worth":
            clean_money(
                find_value(
                    "gross_worth",
                    rows
                )
            )
    }

    logger.info(
        f"Completed → {output['file']}"
    )

    return output


logger.info(
    "Invoice extraction started"
)

if not os.path.exists(INPUT_FOLDER):

    logger.error(
        f"Folder not found → {INPUT_FOLDER}"
    )
    
    raise FileNotFoundError(
        INPUT_FOLDER
    )

records = []

for root, dirs, files in os.walk(INPUT_FOLDER):

    for file in files:

        if file.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        ):

            path = os.path.join(
                root,
                file
            )

            try:

                records.append(
                    process(path)
                )

            except Exception as ex:

                logger.exception(
                    f"Failed → {file}"
                )

df = pd.DataFrame(
    records
)

df.to_csv(
    OUTPUT_CSV,
    index=False
)

logger.info(
    f"CSV generated → {OUTPUT_CSV}"
)

logger.info(
    "Extraction completed"
)