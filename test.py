from paddleocr import PaddleOCR

ocr = PaddleOCR(
    device="cpu",
    ocr_version="PP-OCRv5",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)

ocr_result = ocr.predict("sample.pdf")
print(ocr_result)

print("Extracted Text:")
for outer in ocr_result:
    if outer is not None:
        for line in outer:
            # line[1][0] contains the extracted text string
            print(line[1][0])