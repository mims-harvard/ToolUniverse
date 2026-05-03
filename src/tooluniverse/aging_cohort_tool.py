"""AgingCohort_search tool for ToolUniverse.

Provides a searchable registry of major aging and longitudinal cohort studies
worldwide. Contains curated metadata for ~30 studies including study design,
sample size, variable categories, and data access information.

No external API calls -- uses an internal curated database. Cohort metadata
changes rarely (study design, variables, and access methods are stable).
"""

from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# ---------------------------------------------------------------------------
# Internal cohort database
# ---------------------------------------------------------------------------

_COHORTS: List[Dict[str, Any]] = [
    # === Health & Aging (Longitudinal) ===
    {
        "name": "HRS",
        "full_name": "Health and Retirement Study",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 20000,
        "sample_size_note": "20,000+ respondents; biennial interviews",
        "age_range": "50+",
        "start_year": 1992,
        "waves_or_follow_up": "Biennial waves since 1992 (16+ waves)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "disability",
            "healthcare_utilization",
            "employment",
            "retirement",
            "income",
            "wealth",
        ],
        "description": (
            "Flagship US longitudinal study of adults aged 50+ covering health, "
            "retirement, and aging. Nutrition data available via the 2013 Health "
            "Care and Nutrition Study (HCNS) module, including 24-hour dietary "
            "recall and supplement use. Physical measures include grip strength "
            "and walking speed (since 2006 enhanced face-to-face module). "
            "Genetic data (HRS-GWAS) and dried blood spot biomarkers available."
        ),
        "access_method": "Public-use files freely available; restricted data via application",
        "access_url": "https://hrs.isr.umich.edu/data-products",
        "key_publications": [
            "Sonnega et al. (2014) J Gerontol B 69(Suppl 2):S199-S210",
            "Juster & Suzman (1995) J Human Resources 30:S7-S56",
        ],
    },
    {
        "name": "ELSA",
        "full_name": "English Longitudinal Study of Ageing",
        "country": "UK",
        "design": "longitudinal",
        "sample_size": 12000,
        "sample_size_note": "12,000+ respondents at baseline; refreshment samples added",
        "age_range": "50+",
        "start_year": 2002,
        "waves_or_follow_up": "Biennial waves since 2002 (10+ waves)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "disability",
            "mental_health",
            "social_participation",
            "wealth",
        ],
        "description": (
            "Core UK aging cohort study harmonized with HRS. Measures grip "
            "strength (Smedley dynamometer), walking speed (timed 8-foot walk), "
            "and gait speed in even-numbered waves. Nurse visits collect blood "
            "biomarkers including inflammatory markers, HbA1c, cholesterol. "
            "Dietary data from food frequency questionnaire in selected waves. "
            "Genetic data linked to UK Biobank array."
        ),
        "access_method": "UK Data Service; free registration required",
        "access_url": "https://www.elsa-project.ac.uk/accessing-elsa-data",
        "key_publications": [
            "Steptoe et al. (2013) Int J Epidemiol 42(6):1640-1648",
            "Marmot et al. (2003) J Epidemiol Community Health 57(10):778-783",
        ],
    },
    {
        "name": "SHARE",
        "full_name": "Survey of Health, Ageing and Retirement in Europe",
        "country": "Europe (28 countries)",
        "design": "longitudinal",
        "sample_size": 140000,
        "sample_size_note": "140,000+ respondents across 28 European countries + Israel",
        "age_range": "50+",
        "start_year": 2004,
        "waves_or_follow_up": "Biennial waves since 2004 (9+ waves)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "mental_health",
            "social_networks",
            "employment",
            "retirement",
            "healthcare_utilization",
        ],
        "description": (
            "Pan-European multidisciplinary aging study harmonized with HRS and "
            "ELSA. Covers 28 EU countries plus Israel. Measures grip strength "
            "(Smedley dynamometer), chair stands, and peak flow. Dried blood "
            "spot biomarkers in selected waves. Nutrition questions on fruit/"
            "vegetable consumption frequency. SHARE-GWAS and SHARE-omics "
            "substudies available."
        ),
        "access_method": "Free registration at SHARE Research Data Center",
        "access_url": "https://share-eric.eu/data/data-access",
        "key_publications": [
            "Borsch-Supan et al. (2013) Int J Epidemiol 42(4):992-1001",
            "Borsch-Supan & Jurges (2005) The Survey of Health, Ageing and Retirement in Europe",
        ],
    },
    {
        "name": "InCHIANTI",
        "full_name": "Invecchiare in Chianti (Aging in the Chianti Area)",
        "country": "Italy",
        "design": "longitudinal",
        "sample_size": 1300,
        "sample_size_note": "1,300+ participants from Greve in Chianti and Bagno a Ripoli",
        "age_range": "20+ (enriched for 65+)",
        "start_year": 1998,
        "waves_or_follow_up": "3-year follow-up intervals; 6+ follow-ups through 2019",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "body_composition",
            "muscle_strength",
            "inflammatory_markers",
            "anemia",
            "micronutrients",
        ],
        "description": (
            "Detailed Italian aging study with extensive nutrition and physical "
            "function data. Known for pioneering work on iron status, anemia, "
            "and physical decline in aging. Detailed dietary assessment via "
            "validated food frequency questionnaire (EPIC-FFQ) with nutrient "
            "calculations including iron, zinc, folate, B12, and vitamin D. "
            "Walking speed measured over 4m and 400m courses. Grip strength "
            "via hand dynamometer. Comprehensive blood biomarkers including "
            "serum iron, ferritin, transferrin, hepcidin, IL-6, TNF-alpha, "
            "CRP. GWAS data available."
        ),
        "access_method": "Collaborative access via application to InCHIANTI study group",
        "access_url": "https://inchiantistudy.net/wp/",
        "key_publications": [
            "Ferrucci et al. (2000) J Am Geriatr Soc 48(9):1136-1138",
            "Guralnik et al. (1994) N Engl J Med 332(9):556-562",
        ],
    },
    {
        "name": "TILDA",
        "full_name": "The Irish Longitudinal Study on Ageing",
        "country": "Ireland",
        "design": "longitudinal",
        "sample_size": 8500,
        "sample_size_note": "8,500+ community-dwelling adults aged 50+",
        "age_range": "50+",
        "start_year": 2009,
        "waves_or_follow_up": "Biennial waves since 2009 (6+ waves)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "frailty",
            "bone_density",
            "cardiovascular",
            "vision",
        ],
        "description": (
            "Irish aging cohort harmonized with HRS/ELSA/SHARE. Notable for "
            "comprehensive health assessment centers with objective physical "
            "measures: Timed Up and Go (TUG), grip strength, walking speed, "
            "dual-energy X-ray absorptiometry (DXA). Nutrition assessed via "
            "self-completed food frequency questionnaire. Blood biomarkers "
            "include vitamin D, B12, folate, iron studies, HbA1c. GWAS data "
            "on Illumina Omni array."
        ),
        "access_method": "ISSDA (Irish Social Science Data Archive); application required",
        "access_url": "https://tilda.tcd.ie/data/accessing-data/",
        "key_publications": [
            "Kearney et al. (2011) J Am Geriatr Soc 59(Suppl 2):S291-S299",
            "Whelan & Savva (2013) TILDA Design Report",
        ],
    },
    {
        "name": "BLSA",
        "full_name": "Baltimore Longitudinal Study of Aging",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 3000,
        "sample_size_note": "3,000+ participants; continuous enrollment since 1958",
        "age_range": "20-100+",
        "start_year": 1958,
        "waves_or_follow_up": "Continuous enrollment; visits every 1-4 years depending on age",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "body_composition",
            "imaging",
            "personality",
            "sensory_function",
        ],
        "description": (
            "Oldest continually running scientific study of human aging in the "
            "US (since 1958), conducted by NIA/NIH. Comprehensive phenotyping "
            "every 1-4 years with detailed physical, cognitive, and metabolic "
            "assessments. Nutrition via 7-day food records and dietary recalls. "
            "Physical function battery includes grip strength, walking speed, "
            "400m walk test, and Short Physical Performance Battery (SPPB). "
            "MRI brain imaging, body composition (DXA, CT), and extensive "
            "biobanking."
        ),
        "access_method": "NIA BLSA Data Sharing via application to NIA Intramural Research Program",
        "access_url": "https://www.nia.nih.gov/research/labs/blsa",
        "key_publications": [
            "Shock et al. (1984) Normal Human Aging: The Baltimore Longitudinal Study of Aging",
            "Ferrucci (2008) Exp Gerontol 43(2):84-89",
        ],
    },
    {
        "name": "LASA",
        "full_name": "Longitudinal Aging Study Amsterdam",
        "country": "Netherlands",
        "design": "longitudinal",
        "sample_size": 3000,
        "sample_size_note": "3,000+ at baseline; refreshment cohorts added",
        "age_range": "55-85 at baseline",
        "start_year": 1992,
        "waves_or_follow_up": "3-year follow-up intervals; 10+ waves",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "mental_health",
            "social_functioning",
            "disability",
            "falls",
            "loneliness",
        ],
        "description": (
            "Dutch aging study focused on predictors and consequences of changes "
            "in autonomy and well-being. Detailed physical function measures "
            "including grip strength (Martin Vigorimeter), walking speed (3m "
            "and 6m walks), chair stands, and balance. Nutrition assessed by "
            "dietary history method and food frequency questionnaire. "
            "Biomarkers include 25(OH)D, PTH, cortisol, and inflammatory "
            "markers."
        ),
        "access_method": "Data available via LASA data management team; collaboration application",
        "access_url": "https://www.lasa-vu.nl/data/availability-data/",
        "key_publications": [
            "Huisman et al. (2011) Int J Epidemiol 40(4):868-876",
            "Deeg et al. (2002) J Gerontol B 57(1):P47-P53",
        ],
    },
    {
        "name": "CHARLS",
        "full_name": "China Health and Retirement Longitudinal Study",
        "country": "China",
        "design": "longitudinal",
        "sample_size": 17000,
        "sample_size_note": "17,000+ respondents from 150 counties across China",
        "age_range": "45+",
        "start_year": 2011,
        "waves_or_follow_up": "Biennial waves since 2011 (5+ waves)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "disability",
            "mental_health",
            "healthcare_utilization",
            "income",
        ],
        "description": (
            "Chinese aging study harmonized with HRS/SHARE/ELSA. Measures grip "
            "strength (Yuejian WL-1000 dynamometer), timed walk, chair stands, "
            "and balance. Blood-based biomarkers collected via venous blood "
            "draw. Nutrition assessed through dietary intake questions. "
            "Harmonized cognitive battery including word recall, serial 7s, "
            "and drawing tasks. CHARLS-GWAS data available."
        ),
        "access_method": "Publicly available via CHARLS website after registration",
        "access_url": "https://charls.pku.edu.cn/en/",
        "key_publications": [
            "Zhao et al. (2014) Int J Epidemiol 43(1):61-68",
            "Chen et al. (2019) J Econ Ageing 13:68-87",
        ],
    },
    {
        "name": "JSTAR",
        "full_name": "Japanese Study of Aging and Retirement",
        "country": "Japan",
        "design": "longitudinal",
        "sample_size": 4200,
        "sample_size_note": "4,200+ respondents from 7 municipalities",
        "age_range": "50-75 at baseline",
        "start_year": 2007,
        "waves_or_follow_up": "Biennial waves since 2007 (5+ waves)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "medications",
            "chronic_conditions",
            "mental_health",
            "employment",
            "retirement",
            "social_participation",
        ],
        "description": (
            "Japanese aging panel study harmonized with HRS family. Measures "
            "grip strength, usual walking speed (timed walks), and cognitive "
            "function (word recall, serial subtraction). Nutrition via brief "
            "dietary screener. Covers health, economic status, and social "
            "engagement of middle-aged and older Japanese adults."
        ),
        "access_method": "RIETI Data Inquiry; application required",
        "access_url": "https://www.rieti.go.jp/en/projects/jstar/",
        "key_publications": [
            "Ichimura et al. (2009) RIETI Discussion Paper 09-E-047",
            "Oshio & Shimizutani (2005) J Japanese Int Economies 19:401-426",
        ],
    },
    {
        "name": "KLoSA",
        "full_name": "Korean Longitudinal Study of Aging",
        "country": "South Korea",
        "design": "longitudinal",
        "sample_size": 10000,
        "sample_size_note": "10,000+ nationally representative sample aged 45+",
        "age_range": "45+",
        "start_year": 2006,
        "waves_or_follow_up": "Biennial waves since 2006 (8+ waves)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "grip_strength",
            "physical_function",
            "cognitive",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "disability",
            "mental_health",
            "employment",
            "retirement",
            "income",
        ],
        "description": (
            "Korean aging panel harmonized with HRS family. Grip strength "
            "measured by dynamometer. Cognitive battery includes K-MMSE, "
            "word recall, and serial 7s. Covers demographics, health, "
            "employment, income, assets, and subjective well-being of "
            "middle-aged and older Korean adults."
        ),
        "access_method": "Korea Employment Information Service (KEIS); free download after registration",
        "access_url": "https://survey.keis.or.kr/eng/klosa/klosa01.jsp",
        "key_publications": [
            "Park et al. (2007) Survey Design of the Korean Longitudinal Study of Ageing",
            "Won et al. (2014) Gerontologist 54(Suppl 2):S28-S31",
        ],
    },
    # === Nutrition & Health ===
    {
        "name": "NHANES",
        "full_name": "National Health and Nutrition Examination Survey",
        "country": "USA",
        "design": "cross-sectional",
        "sample_size": 10000,
        "sample_size_note": "~10,000 per 2-year cycle; continuous since 1999",
        "age_range": "All ages (birth to 80+)",
        "start_year": 1999,
        "waves_or_follow_up": "Continuous 2-year cycles; cross-sectional but linked to NDI mortality follow-up",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "micronutrients",
            "grip_strength",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "body_composition",
            "blood_pressure",
            "oral_health",
            "environmental_exposures",
        ],
        "description": (
            "Gold standard US nutrition and health examination survey. Detailed "
            "24-hour dietary recall (2 days) with complete nutrient estimation "
            "including iron (heme and non-heme), zinc, folate, all vitamins. "
            "Laboratory measures include serum iron, ferritin, TIBC, "
            "transferrin saturation, soluble transferrin receptor, CRP, "
            "complete blood count. Grip strength (Takei dynamometer, ages 6+) "
            "since 2011-2012 cycle. Physical function measures for older "
            "adults. GWAS data available in dbGaP."
        ),
        "access_method": "Public-use files freely downloadable; restricted linked data via RDC",
        "access_url": "https://www.cdc.gov/nchs/nhanes/index.htm",
        "key_publications": [
            "Zipf et al. (2013) NCHS Vital Health Stat 1(56)",
            "Johnson et al. (2013) Adv Nutr 4(6):368S-373S",
        ],
    },
    {
        "name": "CHNS",
        "full_name": "China Health and Nutrition Survey",
        "country": "China",
        "design": "longitudinal",
        "sample_size": 30000,
        "sample_size_note": "30,000+ individuals across 15 provinces",
        "age_range": "All ages",
        "start_year": 1989,
        "waves_or_follow_up": "Waves in 1989, 1991, 1993, 1997, 2000, 2004, 2006, 2009, 2011, 2015, 2018",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "micronutrients",
            "physical_activity",
            "physical_function",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "body_composition",
            "blood_pressure",
            "food_security",
            "urbanization",
        ],
        "description": (
            "Major longitudinal nutrition and health survey in China. Detailed "
            "3-day weighed food records with household food inventory. "
            "Comprehensive nutrient calculation including iron (from Chinese "
            "Food Composition Table). Biomarkers include hemoglobin, ferritin, "
            "CRP, HbA1c, lipids, and fasting glucose. Tracks nutrition "
            "transition, urbanization, and health changes in China since 1989."
        ),
        "access_method": "Publicly available via UNC Carolina Population Center",
        "access_url": "https://www.cpc.unc.edu/projects/china",
        "key_publications": [
            "Popkin et al. (2010) Int J Epidemiol 39(6):1435-1440",
            "Zhang et al. (2014) Eur J Clin Nutr 68(4):466-471",
        ],
    },
    {
        "name": "FHS",
        "full_name": "Framingham Heart Study",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 5000,
        "sample_size_note": "5,209 original cohort; Offspring (5,124), Third Gen (4,095), Omni cohorts",
        "age_range": "28-62 (original); multigenerational",
        "start_year": 1948,
        "waves_or_follow_up": "Continuous follow-up since 1948; biennial exams for original cohort",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "cardiovascular",
            "blood_pressure",
            "lipids",
            "diabetes",
            "imaging",
        ],
        "description": (
            "Landmark multigenerational cardiovascular cohort study. "
            "Nutrition data from food frequency questionnaires (Willett FFQ) "
            "in Offspring and Third Generation cohorts. Extensive cardiovascular "
            "phenotyping including ECG, echocardiography, CT coronary calcium, "
            "carotid IMT. Brain MRI and cognitive testing. Whole-genome "
            "sequencing and GWAS data in dbGaP (SHARe/TOPMed). Biomarkers "
            "include lipids, glucose, inflammatory markers, BNP, troponin."
        ),
        "access_method": "BioLINCC (NHLBI) for clinical data; dbGaP for genomic data",
        "access_url": "https://www.framinghamheartstudy.org/",
        "key_publications": [
            "Dawber et al. (1951) Am J Public Health 41(3):279-286",
            "Kannel et al. (1979) Am Heart J 97(2):159-166",
        ],
    },
    {
        "name": "Rotterdam Study",
        "full_name": "Rotterdam Study (Erasmus Rotterdam Health Study)",
        "country": "Netherlands",
        "design": "longitudinal",
        "sample_size": 15000,
        "sample_size_note": "15,000+ participants across 3 sub-cohorts (RS-I, RS-II, RS-III)",
        "age_range": "45+ at enrollment",
        "start_year": 1990,
        "waves_or_follow_up": "Continuous follow-up; examinations every 3-5 years",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "micronutrients",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "cardiovascular",
            "bone_density",
            "imaging",
            "ophthalmology",
        ],
        "description": (
            "Large Dutch population-based cohort with detailed phenotyping "
            "including brain MRI, cardiac CT, retinal imaging, DXA. Nutrition "
            "assessed via validated semiquantitative food frequency "
            "questionnaire (389 items) with detailed nutrient calculations "
            "including iron, calcium, and micronutrients. Physical function: "
            "grip strength, walking speed (timed 15-foot walk), chair stands. "
            "GWAS genotyping on Illumina arrays; whole-genome sequencing "
            "available. Biomarkers include iron studies (ferritin, transferrin "
            "saturation), inflammation, metabolomics."
        ),
        "access_method": "Data management team application; collaboration agreements",
        "access_url": "https://www.erasmusmc.nl/en/research/core-facilities/ergo",
        "key_publications": [
            "Ikram et al. (2020) Eur J Epidemiol 35(8):731-770",
            "Hofman et al. (2015) Eur J Epidemiol 30(8):661-708",
        ],
    },
    {
        "name": "UK Biobank",
        "full_name": "UK Biobank",
        "country": "UK",
        "design": "both",
        "sample_size": 500000,
        "sample_size_note": "~500,000 participants enrolled 2006-2010; imaging subset ~100K",
        "age_range": "40-69 at enrollment",
        "start_year": 2006,
        "waves_or_follow_up": "Baseline + repeat assessments + ongoing imaging study + linkage to health records",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "body_composition",
            "imaging",
            "accelerometry",
            "proteomics",
            "metabolomics",
        ],
        "description": (
            "Largest prospective cohort with deep phenotyping and multi-omics. "
            "Grip strength (Jamar dynamometer), walking pace (self-report and "
            "accelerometer-derived), 6-minute walk distance. Dietary data from "
            "Oxford WebQ 24-hour dietary recall (up to 5 completions) and "
            "touchscreen food frequency questionnaire. Blood biomarkers include "
            "iron, ferritin, transferrin, TIBC, plus 3,000+ protein biomarkers "
            "(Olink Explore 3072). Full WGS, WES, genotyping array, "
            "metabolomics (Nightingale NMR, Metabolon), and proteomics."
        ),
        "access_method": "Approved researchers via UK Biobank Access Management System",
        "access_url": "https://www.ukbiobank.ac.uk/enable-your-research/apply-for-access",
        "key_publications": [
            "Sudlow et al. (2015) PLoS Med 12(3):e1001779",
            "Bycroft et al. (2018) Nature 562(7726):203-209",
        ],
    },
    # === Physical Function Focused ===
    {
        "name": "SEE",
        "full_name": "Salisbury Eye Evaluation Study",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 2500,
        "sample_size_note": "~2,500 participants aged 65+ in Salisbury, Maryland",
        "age_range": "65+",
        "start_year": 1993,
        "waves_or_follow_up": "Follow-up visits at 2, 6, and 8 years",
        "key_variable_categories": [
            "demographics",
            "walking_speed",
            "physical_function",
            "cognitive",
            "vision",
            "disability",
            "falls",
            "medications",
            "chronic_conditions",
        ],
        "description": (
            "Community-based study linking vision impairment to physical "
            "function in older adults. Measured usual walking speed over a "
            "timed course, visual acuity, contrast sensitivity, visual field, "
            "and disability outcomes. Known for establishing walking speed "
            "cut-points predictive of disability."
        ),
        "access_method": "Contact study investigators at Johns Hopkins Wilmer Eye Institute",
        "access_url": "https://www.hopkinsmedicine.org/wilmer/research/",
        "key_publications": [
            "West et al. (1997) Invest Ophthalmol Vis Sci 38(2):557-568",
            "Rubin et al. (2001) Arch Ophthalmol 119(2):169-174",
        ],
    },
    {
        "name": "Health ABC",
        "full_name": "Health, Aging, and Body Composition Study",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 3000,
        "sample_size_note": "3,075 well-functioning adults aged 70-79 at baseline",
        "age_range": "70-79 at enrollment",
        "start_year": 1997,
        "waves_or_follow_up": "Annual visits; 15+ years of follow-up",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "body_composition",
            "muscle_strength",
            "sarcopenia",
            "inflammatory_markers",
            "bone_density",
        ],
        "description": (
            "NIA-funded study designed to investigate the relationship between "
            "body composition and functional decline. Detailed body composition "
            "by DXA and CT (thigh muscle, abdominal fat). Grip strength, "
            "walking speed (20m), 400m walk, knee extensor strength. "
            "Biomarkers include IL-6, TNF-alpha, CRP, insulin, adiponectin. "
            "GWAS data in dbGaP. Key resource for sarcopenia and muscle "
            "aging research."
        ),
        "access_method": "NIA via application; some data in dbGaP",
        "access_url": "https://healthabc.nia.nih.gov/",
        "key_publications": [
            "Newman et al. (2003) J Gerontol A 58(3):M249-M265",
            "Goodpaster et al. (2006) J Gerontol A 61(10):1059-1064",
        ],
    },
    {
        "name": "EPESE",
        "full_name": "Established Populations for Epidemiologic Studies of the Elderly",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 14000,
        "sample_size_note": "~14,000 across 4 US communities (East Boston, Iowa, New Haven, North Carolina)",
        "age_range": "65+",
        "start_year": 1981,
        "waves_or_follow_up": "Annual interviews; physical function assessments at baseline and follow-ups",
        "key_variable_categories": [
            "demographics",
            "walking_speed",
            "physical_function",
            "cognitive",
            "medications",
            "chronic_conditions",
            "disability",
            "mortality",
            "hospitalization",
        ],
        "description": (
            "NIA-funded multi-site study that pioneered physical performance "
            "measures in epidemiologic studies of older adults. Developed the "
            "Short Physical Performance Battery (SPPB) including timed 8-foot "
            "walk, repeated chair stands, and balance tests. Source of seminal "
            "papers linking walking speed to mortality and disability. Hispanic "
            "EPESE extension covers Mexican Americans in the Southwest."
        ),
        "access_method": "ICPSR (Inter-university Consortium for Political and Social Research)",
        "access_url": "https://www.icpsr.umich.edu/web/NACDA/series/59",
        "key_publications": [
            "Cornoni-Huntley et al. (1993) NIA Established Populations for Epidemiologic Studies of the Elderly Resource Data Book",
            "Guralnik et al. (1994) N Engl J Med 332(9):556-562",
        ],
    },
    # === Additional Major Cohorts ===
    {
        "name": "CHS",
        "full_name": "Cardiovascular Health Study",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 5900,
        "sample_size_note": "5,888 adults aged 65+ from 4 US communities",
        "age_range": "65+",
        "start_year": 1989,
        "waves_or_follow_up": "Annual clinic visits through 1999; ongoing follow-up via phone/records",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "cardiovascular",
            "frailty",
            "inflammatory_markers",
        ],
        "description": (
            "NHLBI-funded study of cardiovascular risk factors in older adults. "
            "Known for defining the frailty phenotype (Fried criteria): "
            "unintentional weight loss, self-reported exhaustion, low physical "
            "activity, slow walking speed, and weak grip strength. Walking "
            "speed measured over 15-foot course. Grip strength by Jamar "
            "dynamometer. Comprehensive cardiovascular phenotyping with "
            "echocardiography, carotid ultrasound, and MRI. GWAS data "
            "available."
        ),
        "access_method": "BioLINCC (NHLBI) after approval",
        "access_url": "https://chs-nhlbi.org/",
        "key_publications": [
            "Fried et al. (2001) J Gerontol A 56(3):M146-M156",
            "Fried et al. (1991) Ann Epidemiol 1(3):263-276",
        ],
    },
    {
        "name": "WHAS",
        "full_name": "Women's Health and Aging Studies (WHAS I & II)",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 1600,
        "sample_size_note": "WHAS I: 1,002 (moderate-to-severe disability); WHAS II: 436 (mild-no disability)",
        "age_range": "65+ (WHAS I); 70-79 (WHAS II)",
        "start_year": 1992,
        "waves_or_follow_up": "Semi-annual to annual visits; up to 10 years follow-up",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "micronutrients",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "disability",
            "anemia",
            "inflammatory_markers",
            "frailty",
        ],
        "description": (
            "Landmark studies of the causes and progression of disability in "
            "older women. Extensive biomarker panels including iron studies "
            "(serum iron, ferritin, transferrin saturation, sTfR), "
            "inflammatory markers (IL-6, CRP, TNF-alpha), vitamin D, B12, "
            "carotenoids. Grip strength, walking speed (4m), chair stands, "
            "balance. Nutritional assessment via Block FFQ. Known for seminal "
            "work on anemia, iron deficiency, and physical function in aging."
        ),
        "access_method": "Contact study PI at Johns Hopkins; data sharing via collaboration",
        "access_url": "https://www.jhsph.edu/research/centers-and-institutes/johns-hopkins-center-on-aging-and-health/",
        "key_publications": [
            "Guralnik et al. (1995) J Gerontol A 50(Spec No):M128-M137",
            "Fried et al. (1999) J Clin Epidemiol 52(1):27-37",
        ],
    },
    {
        "name": "HUNT",
        "full_name": "Troendelag Health Study (HUNT)",
        "country": "Norway",
        "design": "longitudinal",
        "sample_size": 230000,
        "sample_size_note": "~230,000 participants across 4 waves (HUNT1-4) in Troendelag county",
        "age_range": "20+ (all adults invited)",
        "start_year": 1984,
        "waves_or_follow_up": "HUNT1 (1984-86), HUNT2 (1995-97), HUNT3 (2006-08), HUNT4 (2017-19)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "cardiovascular",
            "mental_health",
            "metabolomics",
            "blood_pressure",
        ],
        "description": (
            "One of the largest population health surveys in the world, based "
            "in Troendelag county, Norway. Grip strength measured in HUNT3 and "
            "HUNT4. Extensive biobanking with DNA, serum, plasma. GWAS data "
            "on >70,000 participants. Linked to Norwegian health registries "
            "for complete ascertainment of hospitalizations, prescriptions, "
            "and mortality. Diet assessed by food frequency questionnaire."
        ),
        "access_method": "Application to HUNT Research Centre; ethics approval required",
        "access_url": "https://www.ntnu.edu/hunt/data",
        "key_publications": [
            "Krokstad et al. (2013) Int J Epidemiol 42(4):968-977",
            "Holmen et al. (2003) Norsk Epidemiologi 13(1):19-32",
        ],
    },
    {
        "name": "HAPIEE",
        "full_name": "Health, Alcohol and Psychosocial factors In Eastern Europe",
        "country": "Czech Republic, Russia, Poland, Lithuania",
        "design": "longitudinal",
        "sample_size": 36000,
        "sample_size_note": "~36,000 participants across 4 Eastern European countries",
        "age_range": "45-69 at enrollment",
        "start_year": 2002,
        "waves_or_follow_up": "Baseline (2002-2005) + follow-up (2006-2008) + ongoing record linkage",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "cardiovascular",
            "alcohol",
            "psychosocial",
        ],
        "description": (
            "Multi-country study of determinants of cardiovascular disease and "
            "other chronic conditions in Eastern Europe. Measures grip strength, "
            "walking speed (timed walk), chair stands, and cognitive function. "
            "Detailed dietary assessment via food frequency questionnaires "
            "adapted for each country. Blood biomarkers include lipids, "
            "glucose, HbA1c, CRP, fibrinogen. Focus on alcohol consumption "
            "patterns and psychosocial factors."
        ),
        "access_method": "Contact study team at University College London; collaboration required",
        "access_url": "https://www.ucl.ac.uk/epidemiology-health-care/research/epidemiology-and-public-health/research/hapiee",
        "key_publications": [
            "Peasey et al. (2006) BMC Public Health 6:255",
            "Bobak et al. (2004) Eur Heart J 25(23):2075-2076",
        ],
    },
    {
        "name": "CLSA",
        "full_name": "Canadian Longitudinal Study on Aging",
        "country": "Canada",
        "design": "longitudinal",
        "sample_size": 50000,
        "sample_size_note": "~51,000 participants; Tracking (20K telephone) + Comprehensive (31K in-person)",
        "age_range": "45-85 at enrollment",
        "start_year": 2011,
        "waves_or_follow_up": "3-year follow-up intervals planned for 20+ years",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "body_composition",
            "vision",
            "hearing",
            "oral_health",
            "environmental_exposures",
        ],
        "description": (
            "Canada's largest study of aging with comprehensive assessments. "
            "Physical measures include grip strength (Tracker Freedom "
            "dynamometer), 4m walking speed, Timed Up and Go (TUG), and "
            "standing balance. Nutrition assessed via Short Diet Questionnaire "
            "and food security module. Extensive biobanking (blood, urine). "
            "GWAS genotyping available. Linked to Canadian health administrative "
            "data. Measures vision, hearing, and respiratory function."
        ),
        "access_method": "CLSA Data Access Application; approved researchers only",
        "access_url": "https://www.clsa-elcv.ca/data-access",
        "key_publications": [
            "Raina et al. (2009) Can J Aging 28(3):221-229",
            "Raina et al. (2019) Int J Epidemiol 48(6):1752-1753j",
        ],
    },
    {
        "name": "NHATS",
        "full_name": "National Health and Aging Trends Study",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 8000,
        "sample_size_note": "~8,000 Medicare beneficiaries aged 65+; refreshment sample in 2015",
        "age_range": "65+",
        "start_year": 2011,
        "waves_or_follow_up": "Annual interviews since 2011 (12+ rounds)",
        "key_variable_categories": [
            "demographics",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "medications",
            "chronic_conditions",
            "disability",
            "assistive_technology",
            "caregiving",
            "dementia",
            "sensory_function",
            "pain",
        ],
        "description": (
            "Nationally representative study of late-life disability trends and "
            "trajectories in the US. Measures grip strength (Jamar), timed "
            "usual-pace walk, and Short Physical Performance Battery. "
            "Comprehensive disability assessment covering mobility, self-care, "
            "household activities, and technology use. Cognitive testing "
            "includes clock drawing, delayed word recall, and orientation. "
            "Linked to Medicare claims data and National Study of Caregiving "
            "(NSOC) for caregiver data."
        ),
        "access_method": "Restricted and public-use files via NHATS website; DUA required for restricted",
        "access_url": "https://nhats.org/researcher/data-access",
        "key_publications": [
            "Kasper & Freedman (2019) NHATS User Guide",
            "Freedman et al. (2011) J Gerontol B 66(Suppl 1):i206-i214",
        ],
    },
    {
        "name": "MIDUS",
        "full_name": "Midlife in the United States",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 7000,
        "sample_size_note": "~7,000 adults in MIDUS 1; refreshment in MIDUS 3",
        "age_range": "25-74 at MIDUS 1; aging in place",
        "start_year": 1995,
        "waves_or_follow_up": "MIDUS 1 (1995-96), MIDUS 2 (2004-06), MIDUS 3 (2013-14), MIDUS Refresher (2017-22)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "grip_strength",
            "physical_function",
            "cognitive",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "mental_health",
            "psychosocial",
            "stress",
            "sleep",
            "inflammation",
        ],
        "description": (
            "National longitudinal study of health and well-being from midlife "
            "through old age. Unique focus on psychosocial factors, stress, "
            "and their biological consequences. MIDUS Biomarker Project "
            "includes grip strength, waist-hip ratio, salivary cortisol, "
            "inflammatory markers (IL-6, CRP, fibrinogen), and comprehensive "
            "cardiovascular measures. Cognitive battery in MIDUS 2 and 3. "
            "Milwaukee and Japanese (MIDJA) sub-studies for minority and "
            "cross-cultural comparisons."
        ),
        "access_method": "ICPSR (public-use) and NACDA; biomarker data via application",
        "access_url": "https://midus.wisc.edu/data/",
        "key_publications": [
            "Brim et al. (2004) How Healthy Are We? A National Study of Well-Being at Midlife",
            "Ryff et al. (2017) Dev Psychol 53(6):1067-1078",
        ],
    },
    {
        "name": "MESA",
        "full_name": "Multi-Ethnic Study of Atherosclerosis",
        "country": "USA",
        "design": "longitudinal",
        "sample_size": 6800,
        "sample_size_note": "6,814 adults from 6 US communities; 4 racial/ethnic groups",
        "age_range": "45-84 at enrollment",
        "start_year": 2000,
        "waves_or_follow_up": "5 exams over 11 years; ongoing follow-up via records and phone",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "biomarkers",
            "genetics",
            "medications",
            "chronic_conditions",
            "cardiovascular",
            "imaging",
            "air_pollution",
            "proteomics",
            "metabolomics",
        ],
        "description": (
            "Multi-ethnic cohort study of subclinical cardiovascular disease "
            "free of clinical CVD at enrollment. Detailed cardiac imaging "
            "(coronary calcium CT, cardiac MRI). Grip strength measured at "
            "later exams. Walking speed and physical function added in "
            "ancillary studies. Diet assessed via Block FFQ with ethnic-"
            "specific modifications. GWAS, WGS, methylation, proteomics, "
            "and metabolomics data available. Focus on health disparities "
            "across White, Black, Hispanic, and Chinese-American participants."
        ),
        "access_method": "BioLINCC (NHLBI) and MESA Coordinating Center; dbGaP for genomics",
        "access_url": "https://www.mesa-nhlbi.org/",
        "key_publications": [
            "Bild et al. (2002) Am J Epidemiol 156(9):871-881",
            "Burke et al. (2016) J Am Heart Assoc 5(3):e002640",
        ],
    },
    {
        "name": "ALSA",
        "full_name": "Australian Longitudinal Study of Ageing",
        "country": "Australia",
        "design": "longitudinal",
        "sample_size": 2000,
        "sample_size_note": "~2,087 participants aged 70+ from Adelaide, South Australia",
        "age_range": "70+",
        "start_year": 1992,
        "waves_or_follow_up": "13 waves over 18 years (1992-2010)",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "grip_strength",
            "walking_speed",
            "physical_function",
            "cognitive",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "disability",
            "social_networks",
            "depression",
            "sensory_function",
        ],
        "description": (
            "Australian aging cohort with comprehensive assessment of health, "
            "social, and economic aspects of aging. Physical performance "
            "measures include grip strength, walking speed (timed 3m walk), "
            "and balance. Dietary intake assessed by food frequency "
            "questionnaire. Blood biomarkers collected at clinical assessments. "
            "Cognitive testing includes MMSE and detailed neuropsychological "
            "battery."
        ),
        "access_method": "Flinders University Centre for Ageing Studies; application required",
        "access_url": "https://www.flinders.edu.au/college-education-psychology-social-work/alsa",
        "key_publications": [
            "Andrews et al. (2002) Australasian J Ageing 21(4):169-176",
            "Luszcz et al. (2014) Int J Epidemiol 43(6):1829-1830",
        ],
    },
    {
        "name": "HELIAD",
        "full_name": "Hellenic Longitudinal Investigation of Ageing and Diet",
        "country": "Greece",
        "design": "longitudinal",
        "sample_size": 2000,
        "sample_size_note": "~2,000 participants from Larissa and Marousi, Greece",
        "age_range": "65+",
        "start_year": 2009,
        "waves_or_follow_up": "Follow-up visits every 3 years",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "micronutrients",
            "grip_strength",
            "physical_function",
            "cognitive",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "mediterranean_diet",
            "dementia",
        ],
        "description": (
            "Greek aging cohort with special focus on the Mediterranean diet "
            "and cognitive decline. Detailed dietary assessment via "
            "semiquantitative food frequency questionnaire (EPIC-Greece) with "
            "comprehensive nutrient calculations including iron, B-vitamins, "
            "antioxidants. Mediterranean Diet Score (MedDietScore) calculated. "
            "Physical function measures include grip strength. Comprehensive "
            "neuropsychological assessment for dementia and mild cognitive "
            "impairment."
        ),
        "access_method": "Collaboration with HELIAD investigators at National and Kapodistrian University of Athens",
        "access_url": "https://www.heliad.org/",
        "key_publications": [
            "Dardiotis et al. (2014) Neuroepidemiology 43(3-4):263-275",
            "Scarmeas et al. (2018) Alzheimers Dement 14(12):1553-1562",
        ],
    },
    {
        "name": "ATTICA",
        "full_name": "ATTICA Study",
        "country": "Greece",
        "design": "longitudinal",
        "sample_size": 3000,
        "sample_size_note": "3,042 adults from the greater Athens area",
        "age_range": "18+ at enrollment",
        "start_year": 2001,
        "waves_or_follow_up": "Baseline (2001-02) + 5-year + 10-year + 20-year follow-ups",
        "key_variable_categories": [
            "demographics",
            "nutrition",
            "diet",
            "iron",
            "micronutrients",
            "biomarkers",
            "medications",
            "chronic_conditions",
            "cardiovascular",
            "inflammatory_markers",
            "mediterranean_diet",
            "oxidative_stress",
        ],
        "description": (
            "Greek cardiovascular cohort study with extensive nutritional and "
            "inflammatory biomarker data. Dietary assessment via validated "
            "semiquantitative FFQ with detailed iron and micronutrient "
            "calculations. Mediterranean diet adherence scored. Blood "
            "biomarkers include iron, ferritin, hsCRP, IL-6, TNF-alpha, "
            "fibrinogen, homocysteine, oxidized LDL, adiponectin, and lipids. "
            "Focus on cardiovascular risk, metabolic syndrome, and "
            "inflammation."
        ),
        "access_method": "Collaboration with ATTICA investigators at Harokopio University",
        "access_url": "https://www.hua.gr/en/",
        "key_publications": [
            "Pitsavos et al. (2003) BMC Public Health 3:32",
            "Panagiotakos et al. (2007) J Am Coll Cardiol 49(22):2226-2233",
        ],
    },
]


def _token_match_count(text: str, tokens: list[str]) -> int:
    """Return how many query tokens appear in text."""
    lower = text.lower()
    return sum(1 for tok in tokens if tok in lower)


def _cohort_searchable_text(c: Dict[str, Any]) -> str:
    """Build a single searchable string from all cohort fields."""
    parts = [
        c.get("name", ""),
        c.get("full_name", ""),
        c.get("country", ""),
        c.get("design", ""),
        c.get("description", ""),
        c.get("age_range", ""),
        c.get("waves_or_follow_up", ""),
        c.get("sample_size_note", ""),
    ]
    parts.extend(c.get("key_variable_categories", []))
    parts.extend(c.get("key_publications", []))
    return " ".join(parts).lower()


@register_tool("AgingCohortSearchTool")
class AgingCohortSearchTool(BaseTool):
    """Search a curated registry of major aging and longitudinal cohort studies."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._run(arguments)
        except Exception as e:
            return {"status": "error", "error": str(e), "retryable": False}

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        country = (arguments.get("country") or "").strip()
        design = (arguments.get("design") or "").strip().lower()
        min_sample_size = arguments.get("min_sample_size")
        has_variable = (arguments.get("has_variable") or "").strip().lower()

        if not query:
            return {
                "status": "error",
                "error": "query is required",
                "retryable": False,
            }

        # Tokenize query -- match at least one token, rank by coverage
        tokens = query.lower().split()
        scored: list[tuple[int, Dict[str, Any]]] = []

        for cohort in _COHORTS:
            searchable = _cohort_searchable_text(cohort)
            hits = _token_match_count(searchable, tokens)
            if hits == 0:
                continue

            # --- Optional filters ---
            if country and country.lower() not in cohort.get("country", "").lower():
                continue

            if design and design != "both":
                cohort_design = cohort.get("design", "")
                if design == "longitudinal" and cohort_design not in (
                    "longitudinal",
                    "both",
                ):
                    continue
                if design == "cross-sectional" and cohort_design not in (
                    "cross-sectional",
                    "both",
                ):
                    continue

            if min_sample_size is not None:
                if (cohort.get("sample_size") or 0) < min_sample_size:
                    continue

            if has_variable:
                categories = [
                    v.lower() for v in cohort.get("key_variable_categories", [])
                ]
                # Match whole category names or tokens within underscore-delimited names
                if not any(
                    has_variable == cat or has_variable in cat.split("_")
                    for cat in categories
                ):
                    continue

            scored.append((hits, cohort))

        # Sort by number of matching tokens (descending), then by name
        scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))
        results = [item for _, item in scored]

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "filters_applied": {
                    k: v
                    for k, v in {
                        "country": country or None,
                        "design": design or None,
                        "min_sample_size": min_sample_size,
                        "has_variable": has_variable or None,
                    }.items()
                    if v is not None
                },
                "total_matched": len(results),
                "total_in_registry": len(_COHORTS),
            },
        }
