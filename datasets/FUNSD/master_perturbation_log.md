# 📝 Master Perturbation Log

This log details the specific transformations applied to create the Doc B augmented dataset.

## 📄 Document: `0001129658`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `Fax Cover Sheet` | `Facsimile Transmission Cover` | *exact_match* |
| Document_Date | `10/13/99` | `October 13, 1999` | *semantic_equivalence* |
| Contact_Number | `305 400-6107` | `305-400-6108` | *conflict* |
| Reference_ID | `4162/158` | `4162-158-REV` | *exact_match* |
| Organization_Name | `Winston & Strawn` | `Winston and Strawn LLP` | *semantic_equivalence* |

---

## 📄 Document: `0001463282`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `MARKETING RESEARCH AUTHORIZATION` | `MARKET RESEARCH APPROVAL FORM` | *exact_match* |
| Document_Date | `4/16/90` | `April 16, 1990` | *semantic_equivalence* |
| Total_Amount | `35,675` | `35675.00` | *exact_match* |
| Percentage_Value | `10%` | `0.10` | *semantic_equivalence* |
| Quantity_Count | `400` | `450` | *conflict* |
| Signature_Date | `5/3/90` | `5/4/90` | *conditional* |

---

## 📄 Document: `0011838621`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `INTERNATIONAL MARKETING RESEARCH CHANGE OF AUTHORIZED COST` | `INTERNATIONAL MARKETING RESEARCH AUTHORIZATION ADJUSTMENT FORM` | *exact_match* |
| Document_Date | `6/21/90` | `June 21, 1990` | *semantic_equivalence* |
| Total_Amount | `47,711.47` | `47711.47` | *exact_match* |
| Percentage_Value | `10%` | `12%` | *conflict* |
| Reference_ID | `27` | `28` | *exact_match* |
| Total_Amount | `47,711.47` | `47711.47` | *formula_validation* |

---

## 📄 Document: `0011845203`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `BROWN & WILLIAMSON BID REQUEST FORM` | `BROWN & WILLIAMSON PROPOSAL SOLICITATION DOCUMENT` | *exact_match* |
| Reference_ID | `1991-18` | `1991-19` | *conflict* |
| Document_Date | `3/1/91` | `March 1, 1991` | *semantic_equivalence* |
| Contact_Number | `1-502-568-8092` | `(502) 568-8092` | *semantic_equivalence* |
| Person_Name | `Mary D. Davis` | `Mary Davis` | *exact_match* |
| Threshold_Requirement | `TWO SECTIONS` | `3` | *conditional* |

---

## 📄 Document: `0011974919`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Document_Date | `September 10, 1996` | `1996-09-10` | *semantic_equivalence* |
| Quantity_Count | `300` | `350` | *conflict* |
| Percentage_Value | `100.00 %` | `0.5` | *semantic_equivalence* |
| Total_Amount | `300` | `150` | *derived_value* |
| Reference_ID | `602399` | `REF-602399-X` | *exact_match* |

---

## 📄 Document: `0012529284`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `CHANGE OF AUTHORIZED COST` | `MODIFICATION OF AUTHORIZED EXPENDITURE` | *exact_match* |
| Document_Date | `12-4-87` | `December 4, 1987` | *semantic_equivalence* |
| Percentage_Value | `10%` | `12%` | *conflict* |
| Total_Amount | `212,475` | `215,000` | *derived_value* |
| Reference_ID | `C-51` | `C-52` | *exact_match* |

---

## 📄 Document: `0012529295`
**Total Perturbations:** 7

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Document_Date | `10/9/87` | `October 9, 1987` | *semantic_equivalence* |
| Reference_ID | `C-40` | `C-41` | *exact_match* |
| Percentage_Value | `10%` | `0.10` | *semantic_equivalence* |
| Total_Amount | `780,900.00` | `780900` | *exact_match* |
| Quantity_Count | `1,500` | `1500` | *exact_match* |
| Total_Amount | `-70,825.00` | `-70825.01` | *conflict* |
| Total_Amount | `1,233,308.08` | `1233308.08` | *formula_validation* |

---

## 📄 Document: `0012602424`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `CHANGE OF AUTHORIZED COST` | `MODIFICATION OF AUTHORIZED EXPENDITURE` | *exact_match* |
| Document_Date | `11/28/84` | `1984-11-28` | *semantic_equivalence* |
| Percentage_Value | `0.5%` | `0.005` | *semantic_equivalence* |
| Total_Amount | `221,000` | `221000.00` | *derived_value* |
| Reference_ID | `NP-75` | `NP-76` | *conflict* |
| Signature_Date | `12/11` | `1984-12-11` | *semantic_equivalence* |

---

## 📄 Document: `0012947358`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Document_Date | `1-27-69` | `January 27, 1969` | *semantic_equivalence* |
| Total_Amount | `$5,000` | `$5,500` | *conflict* |
| Company_Address | `245 Park Avenue, New York, New York 10017` | `245 Park Ave, NY, NY 10017` | *exact_match* |
| Signature_Date | `1/29/69` | `01/29/1969` | *semantic_equivalence* |
| Threshold_Requirement | `20 days` | `20` | *conditional* |
| Reference_ID | `69-1351` | `REF-69-1351` | *exact_match* |

---

## 📄 Document: `0060029036`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `DOCUMENT CLEARANCE SHEET` | `DOCUMENT APPROVAL FORM` | *exact_match* |
| Reference_ID | `4011 00 00` | `4011-00-00` | *semantic_equivalence* |
| Document_Date | `January 11, 1994` | `01/11/1994` | *semantic_equivalence* |
| Total_Amount | `$1,340,000.00` | `$1,340,000.01` | *conflict* |
| Threshold_Requirement | `OVER $25,000` | `25000` | *derived_value* |
| Signature_Date | `1-11-94` | `1994-01-12` | *conditional* |

---

## 📄 Document: `0060068489`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `ADVERTISING AND SELLING AUTHORIZATION` | `ADVERTISING AND SALES AUTHORIZATION` | *exact_match* |
| Document_Date | `3/17/82` | `March 17, 1982` | *semantic_equivalence* |
| Quantity_Count | `1,680` | `1700` | *conflict* |
| Total_Amount | `$ 28,880.00` | `$ 29,200.00` | *derived_value* |
| Rate_or_Price | `$16.00` | `16.00` | *formula_validation* |

---

## 📄 Document: `0060136394`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `CHANGE IN RADIO SCHEDULE` | `RADIO BROADCAST SCHEDULE AMENDMENT` | *exact_match* |
| Reference_ID | `RS#39` | `RS-0039-REV` | *exact_match* |
| Signature_Date | `APRIL 1, 1957` | `04/01/1957` | *semantic_equivalence* |
| Total_Amount | `$ 6,600.00` | `$ 6,500.00` | *conflict* |
| Rate_or_Price | `$ 150.00` | `150.00` | *derived_value* |

---

## 📄 Document: `0060165115`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Reference_ID | `2463` | `REF-2463-X` | *exact_match* |
| Document_Date | `28. Apr. 98` | `1998-04-28` | *semantic_equivalence* |
| Total_Page_Count | `21` | `22` | *conflict* |
| Contact_Number | `0041-32-888 5776` | `+41 32 888 5776` | *semantic_equivalence* |
| Recipient_Name | `Dr. Don Leyden` | `Dr. Donald Leyden` | *exact_match* |
| Threshold_Requirement | `null` | `If pages > 20, include appendix` | *conditional* |

---

## 📄 Document: `0060214859`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Reference_ID | `517` | `REP-00517` | *exact_match* |
| Document_Date | `10-NOV-1986` | `1986-11-10` | *semantic_equivalence* |
| Quantity_Count | `2` | `4` | *conflict* |
| Percentage_Value | `2.49%` | `0.0249` | *semantic_equivalence* |
| Threshold_Requirement | `190-210` | `180-220` | *conflict* |
| Contact_Number | `6926` | `EXT-6926` | *exact_match* |

---

## 📄 Document: `00837285`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `COMPOUND PHYSICAL PARAMETERS` | `CHEMICAL COMPOUND DATA SHEET` | *exact_match* |
| Document_Date | `11/13/81` | `November 13, 1981` | *semantic_equivalence* |
| Quantity_Count | `5g` | `5000mg` | *semantic_equivalence* |
| Percentage_Value | `50%` | `45%` | *conflict* |
| Total_Amount | `0.2 ml` | `1.0 ml` | *derived_value* |
| Signature_Date | `1/6/82` | `01/06/1982` | *semantic_equivalence* |

---

## 📄 Document: `00920222`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `PURCHASE REQUISITION` | `PURCHASE ORDER FORM` | *exact_match* |
| Document_Date | `March 27, 1984` | `1984-03-27` | *semantic_equivalence* |
| Rate_or_Price | `$2050` | `$2100` | *conflict* |
| Total_Amount | `$4100` | `$4200` | *derived_value* |
| Contact_Number | `(919) 373-6663` | `919-373-6663` | *semantic_equivalence* |

---

## 📄 Document: `01150773_01150774`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Organization_Name | `COVINGTON & BURLING` | `Covington and Burling LLP` | *exact_match* |
| Document_Date | `January 15, 1997` | `1997-01-15` | *semantic_equivalence* |
| Total_Page_Count | `7` | `8` | *conflict* |
| Contact_Number | `(202) 662-6000` | `+1-202-662-6000` | *semantic_equivalence* |
| Recipient_Name | `Mark Berlind` | `M. Berlind` | *exact_match* |

---

## 📄 Document: `11508234`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `MARKETING RESEARCH AUTHORIZATION` | `MARKETING RESEARCH APPROVAL FORM` | *exact_match* |
| Reference_ID | `1995-48D` | `1995-48E` | *conflict* |
| Document_Date | `March 3, 1995` | `03/03/1995` | *semantic_equivalence* |
| Total_Amount | `29,500` | `29500.00` | *semantic_equivalence* |
| Signature_Date | `3/3/95` | `03/03/1995` | *semantic_equivalence* |
| Threshold_Requirement | `$100,000` | `$150,000` | *derived_value* |

---

## 📄 Document: `11875011`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `BID REQUEST FORM` | `REQUEST FOR BID PROPOSAL` | *exact_match* |
| Reference_ID | `1995-13D` | `1995-13D-REV1` | *conflict* |
| Document_Date | `1-23-95` | `January 23, 1995` | *semantic_equivalence* |
| Contact_Number | `(502) 568-7313` | `+1-502-568-7313` | *semantic_equivalence* |
| Threshold_Requirement | `9:00 AM EST` | `12:00 PM EST` | *conditional* |
| Total_Page_Count | `TWO SECTIONS` | `3` | *derived_value* |

---

## 📄 Document: `12603270`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `CHANGE OF AUTHORIZED COST` | `MODIFICATION OF AUTHORIZED EXPENDITURE` | *exact_match* |
| Document_Date | `June 21, 1985` | `06/21/1985` | *semantic_equivalence* |
| Total_Amount | `$ 58,500` | `$ 58,500.00` | *semantic_equivalence* |
| Percentage_Value | `-100%` | `-1.0` | *semantic_equivalence* |
| Reference_ID | `#51` | `#52` | *conflict* |
| Signature_Date | `6/26/85` | `06/27/85` | *conditional* |

---

## 📄 Document: `13149651`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `FISCAL ESTIMATE` | `BUDGETARY ESTIMATION REPORT` | *exact_match* |
| Reference_ID | `LRB 1946` | `LRB-1946-REV` | *exact_match* |
| Rate_or_Price | `$4.50` | `$4.75` | *conflict* |
| Total_Amount | `$8,000` | `$8,500` | *derived_value* |
| Signature_Date | `2-2-83` | `February 2, 1983` | *semantic_equivalence* |
| Organization_Name | `University of Wisconsin System` | `UWS Administrative Office` | *exact_match* |

---

## 📄 Document: `71341634`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `Request For Home Office Check` | `Request For Corporate Office Payment` | *exact_match* |
| Document_Date | `03/24/99` | `March 24, 1999` | *semantic_equivalence* |
| Total_Amount | `$156,686.60` | `$156,686.61` | *conflict* |
| Quantity_Count | `50,758` | `50758` | *exact_match* |
| Payment_Method | `Check` | `Electronic Funds Transfer` | *conditional* |

---

## 📄 Document: `81749056_9057`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Document_Date | `12/08/97` | `December 8, 1997` | *semantic_equivalence* |
| Total_Page_Count | `002/003` | `3` | *exact_match* |
| Quantity_Count | `2,471` | `2470` | *conflict* |
| Percentage_Value | `22%` | `0.22` | *semantic_equivalence* |
| Coupon_Value | `30¢` | `$0.30` | *semantic_equivalence* |
| Coupon_Value | `$3.00` | `$3.50` | *conditional* |

---

## 📄 Document: `87682908`
**Total Perturbations:** 5

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `46TH TCRC REGISTRATION FORM` | `46th Tobacco Chemists' Research Conference Registration Form` | *exact_match* |
| Reference_ID | `87682908` | `87682909` | *conflict* |
| Rate_or_Price | `$ 170.00` | `170.00 CAD` | *semantic_equivalence* |
| Total_Amount | `N/A` | `210.00` | *derived_value* |
| Contact_Number | `(613) 238-2799` | `+1-613-238-2799` | *semantic_equivalence* |

---

## 📄 Document: `88547278_88547279`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `Quotation Request` | `Price Quote Inquiry` | *exact_match* |
| Document_Date | `July 7, 1993` | `07/07/1993` | *semantic_equivalence* |
| Quantity_Count | `89,725` | `90000` | *conflict* |
| Total_Amount | `$16,158` | `$16,500` | *derived_value* |
| Reference_ID | `4854-5` | `AG-4854-5` | *exact_match* |
| Threshold_Requirement | `14 working days` | `10 working days` | *conditional* |

---

## 📄 Document: `89867723`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Document_Date | `April 27, 1981` | `27/04/1981` | *semantic_equivalence* |
| Reference_ID | `5546/1481` | `5546-1481` | *exact_match* |
| Total_Amount | `$6,816` | `$7,497.60` | *derived_value* |
| Percentage_Value | `10%` | `0.10` | *semantic_equivalence* |
| Quantity_Count | `Three` | `3` | *semantic_equivalence* |
| Threshold_Requirement | `10+` | `12` | *conflict* |

---

## 📄 Document: `91372360`
**Total Perturbations:** 4

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Organization_Name | `Lorillard Tobacco Company` | `Lorillard Tobacco Corp.` | *exact_match* |
| Document_Date | `11/4/93` | `November 4, 1993` | *semantic_equivalence* |
| Total_Page_Count | `3` | `5` | *conflict* |
| Contact_Number | `(405) 840-0639` | `405-840-0639` | *semantic_equivalence* |

---

## 📄 Document: `91914407`
**Total Perturbations:** 4

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `FACSIMILE COVER PAGE` | `FAX TRANSMISSION SHEET` | *exact_match* |
| Document_Date | `6-29-94` | `June 29, 1994` | *semantic_equivalence* |
| Total_Page_Count | `14` | `15` | *conflict* |
| Recipient_Name | `Mr. Al Giacoio` | `Al Giacoio` | *exact_match* |

---

## 📄 Document: `92298125`
**Total Perturbations:** 4

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Organization_Name | `AB Research Associates, Inc.` | `AB Research Associates, LLC` | *exact_match* |
| Document_Date | `JAN 19, 1995` | `01/19/1995` | *semantic_equivalence* |
| Total_Page_Count | `16` | `18` | *conflict* |
| Quantity_Count | `13` | `15` | *derived_value* |

---

## 📄 Document: `93380187`
**Total Perturbations:** 6

| Entity Name | Original (Doc A) | Augmented (Doc B) | Transformation Type |
| :--- | :--- | :--- | :--- |
| Form_Title | `COUPON CODE REGISTRATION FORM` | `COUPON REGISTRATION DOCUMENT` | *exact_match* |
| Issue_Date | `MAY 1992` | `05/01/1992` | *semantic_equivalence* |
| Coupon_Value | `50c` | `0.50 USD` | *semantic_equivalence* |
| Percentage_Value | `80%` | `85%` | *conflict* |
| Signature_Date | `JANUARY 8, 1992` | `1992-01-08` | *semantic_equivalence* |
| Reference_ID | `532188` | `532189` | *conditional* |

---

