from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.locations.models import Municipality
from apps.organizations.models import GovernmentOffice, GovernmentOrganization
from apps.processes import services
from apps.processes.models import (
    Process,
    ProcessCategory,
    ProcessFAQ,
    ProcessRequirement,
    ProcessSource,
    ProcessStep,
    ProcessVariant,
)

TODAY = date.today()


class Command(BaseCommand):
    help = (
        "Seed three real, source-cited example processes (company registration, PAN, "
        "passport) researched from official Nepal government sources. Run "
        "`seed_locations` first."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        publisher = User.objects.filter(is_superuser=True).order_by("id").first()
        if publisher is None:
            raise CommandError("No superuser found - run `manage.py createsuperuser` first.")

        try:
            kathmandu = Municipality.objects.get(code="ktm-metro")
        except Municipality.DoesNotExist as exc:
            raise CommandError("Run `manage.py seed_locations` first.") from exc

        business_category, _ = ProcessCategory.objects.get_or_create(
            slug="business", defaults={"name": "Business", "name_np": "व्यवसाय", "order": 1}
        )
        travel_category, _ = ProcessCategory.objects.get_or_create(
            slug="travel-documents",
            defaults={"name": "Travel & Documents", "name_np": "यात्रा र कागजातहरू", "order": 2},
        )

        ocr, _ = GovernmentOrganization.objects.get_or_create(
            slug="office-of-the-company-registrar",
            defaults={
                "name": "Office of the Company Registrar",
                "type": GovernmentOrganization.OrganizationType.DEPARTMENT,
                "website_url": "https://ocr.gov.np/",
                "description": (
                    "Under the Ministry of Industry, Commerce and Supply. Registers and "
                    "administers companies in Nepal via the CAMIS online portal."
                ),
            },
        )
        ird, _ = GovernmentOrganization.objects.get_or_create(
            slug="inland-revenue-department",
            defaults={
                "name": "Inland Revenue Department",
                "type": GovernmentOrganization.OrganizationType.DEPARTMENT,
                "website_url": "https://ird.gov.np/",
                "description": (
                    "Under the Ministry of Finance. Administers income tax, VAT, and PAN "
                    "(Permanent Account Number) registration."
                ),
            },
        )
        dop, _ = GovernmentOrganization.objects.get_or_create(
            slug="department-of-passports",
            defaults={
                "name": "Department of Passports",
                "type": GovernmentOrganization.OrganizationType.DEPARTMENT,
                "website_url": "https://nepalpassport.gov.np/",
                "description": (
                    "Under the Ministry of Foreign Affairs. Issues passports to Nepali "
                    "citizens and travel documents."
                ),
            },
        )

        ocr_office, _ = GovernmentOffice.objects.get_or_create(
            organization=ocr,
            name="Office of the Company Registrar - Head Office",
            defaults={"municipality": kathmandu, "address": "Tripureshwor, Kathmandu", "phone": "9700004414"},
        )
        ird_office, _ = GovernmentOffice.objects.get_or_create(
            organization=ird,
            name="Inland Revenue Department - Head Office",
            defaults={"municipality": kathmandu, "address": "Das Tower, Lazimpat, Kathmandu", "phone": "01-4415802"},
        )
        dop_office, _ = GovernmentOffice.objects.get_or_create(
            organization=dop,
            name="Department of Passports - Head Office",
            defaults={"municipality": kathmandu, "address": "Tripureshwor, Kathmandu", "phone": "01-5970330"},
        )

        created = []
        created.append(self._seed_company_registration(business_category, ocr, ocr_office, publisher))
        created.append(self._seed_pan_registration(business_category, ird, ird_office, publisher))
        created.append(self._seed_passport(travel_category, dop, dop_office, publisher))

        newly_created = sum(1 for flag in created if flag)
        self.stdout.write(self.style.SUCCESS(f"Seeded processes: {newly_created} newly created, {3 - newly_created} already existed."))

    def _seed_company_registration(self, category, org, office, publisher):
        process, created = Process.objects.get_or_create(
            slug="register-a-private-limited-company",
            defaults={
                "title": "Register a Private Limited Company",
                "title_np": "प्राइभेट लिमिटेड कम्पनी दर्ता गर्नुहोस्",
                "category": category,
                "responsible_organization": org,
                "summary": (
                    "Company registration in Nepal: register a private limited company through "
                    "the Office of the Company Registrar's CAMIS online portal."
                ),
                "summary_np": (
                    "कम्पनी दर्ता प्रक्रिया: कम्पनी रजिष्ट्रारको कार्यालयको CAMIS अनलाइन पोर्टलमार्फत "
                    "नेपालमा प्राइभेट लिमिटेड कम्पनी दर्ता गर्नुहोस्।"
                ),
                "description": (
                    "A private limited company is registered with the Office of the Company "
                    "Registrar (OCR) under the Companies Act, 2063 (2006). The entire process - "
                    "name reservation, document submission, and fee payment - runs through the "
                    "CAMIS (Company Administration and Management Information System) online "
                    "portal at camis.ocr.gov.np; an in-person visit is generally not required."
                ),
                "description_np": (
                    "कम्पनी ऐन, २०६३ अन्तर्गत कम्पनी रजिष्ट्रारको कार्यालय (OCR) मा प्राइभेट लिमिटेड कम्पनी "
                    "दर्ता गरिन्छ। नाम आरक्षण, कागजात पेश गर्ने, र शुल्क भुक्तानी लगायत सम्पूर्ण प्रक्रिया "
                    "camis.ocr.gov.np स्थित CAMIS अनलाइन पोर्टलमार्फत हुन्छ; सामान्यतया कार्यालय स्वयं जानु पर्दैन।"
                ),
                "eligibility": (
                    "Any individual(s) or entities eligible under the Companies Act, 2063 can "
                    "promote and register a company. At least one promoter is required for a "
                    "private company."
                ),
                "eligibility_np": (
                    "कम्पनी ऐन, २०६३ अन्तर्गत योग्य कुनै पनि व्यक्ति वा संस्थाले कम्पनी प्रवर्द्धन र दर्ता गर्न "
                    "सक्छ। प्राइभेट कम्पनीको लागि कम्तीमा एक प्रवर्द्धक आवश्यक हुन्छ।"
                ),
                "estimated_duration_min_days": 7,
                "estimated_duration_max_days": 10,
                "total_fee_note": (
                    "NPR 1,000-43,000+ depending on authorized capital (private company); "
                    "see the fee schedule for exact tiers."
                ),
                "total_fee_note_np": (
                    "अधिकृत पूँजीको आधारमा NPR १,०००-४३,०००+ (प्राइभेट कम्पनी); ठ्याक्कै दरका लागि शुल्क "
                    "तालिका हेर्नुहोस्।"
                ),
                "meta_title": "How to Register a Private Limited Company in Nepal",
                "meta_title_np": "नेपालमा प्राइभेट लिमिटेड कम्पनी कसरी दर्ता गर्ने",
                "meta_description": (
                    "Step-by-step guide to registering a private limited company with Nepal's "
                    "Office of the Company Registrar (OCR), with official fees and required documents."
                ),
                "meta_description_np": (
                    "नेपालको कम्पनी रजिष्ट्रारको कार्यालय (OCR) मा प्राइभेट लिमिटेड कम्पनी दर्ता गर्ने "
                    "चरणबद्ध मार्गदर्शन, आधिकारिक शुल्क र आवश्यक कागजातहरूसहित।"
                ),
            },
        )
        if not created:
            return False

        ProcessStep.objects.create(
            process=process, order=1, title="Check and reserve a company name",
            title_np="कम्पनीको नाम जाँच र आरक्षण गर्नुहोस्",
            description="Search for name availability and reserve your proposed company name through the OCR website (ocr.gov.np).",
            description_np="OCR वेबसाइट (ocr.gov.np) मार्फत नाम उपलब्धता खोज्नुहोस् र आफ्नो प्रस्तावित कम्पनीको नाम आरक्षण गर्नुहोस्।",
        )
        ProcessStep.objects.create(
            process=process, order=2, title="Prepare Memorandum and Articles of Association",
            title_np="प्रबन्धपत्र र नियमावली तयार गर्नुहोस्",
            description="Draft the Memorandum of Association (MOA) and Articles of Association (AOA) for the company.",
            description_np="कम्पनीको लागि प्रबन्धपत्र (MOA) र नियमावली (AOA) मस्यौदा तयार गर्नुहोस्।",
        )
        ProcessStep.objects.create(
            process=process, order=3, title="Submit the registration application via CAMIS",
            title_np="CAMIS मार्फत दर्ता आवेदन पेश गर्नुहोस्",
            description="Create an account and submit the application, MOA, AOA, and promoter documents online through camis.ocr.gov.np.",
            description_np="camis.ocr.gov.np मा खाता बनाई आवेदन, MOA, AOA, र प्रवर्द्धकका कागजातहरू अनलाइन पेश गर्नुहोस्।",
            office=office,
        )
        ProcessStep.objects.create(
            process=process, order=4, title="Pay the registration fee",
            title_np="दर्ता शुल्क बुझाउनुहोस्",
            description=(
                "Pay the tiered registration fee based on authorized capital, online through "
                "the CAMIS portal or, for amounts above NPR 5,000, via deposit to OCR's Rajaswa "
                "account at Nepal Rastra Bank."
            ),
            description_np=(
                "अधिकृत पूँजीको आधारमा तोकिएको दर्ता शुल्क CAMIS पोर्टलमार्फत अनलाइन वा NPR ५,००० भन्दा "
                "बढी भए नेपाल राष्ट्र बैंकमा रहेको OCR को राजस्व खातामा जम्मा गरेर बुझाउनुहोस्।"
            ),
            fee_note="NPR 1,000 (up to NPR 1 lakh capital) up to NPR 43,000+ for larger private companies.",
            fee_note_np="NPR १,००० (१ लाखसम्मको पूँजी) देखि ठूला प्राइभेट कम्पनीका लागि NPR ४३,०००+ सम्म।",
        )
        ProcessStep.objects.create(
            process=process, order=5, title="Receive the certificate of incorporation",
            title_np="स्थापना प्रमाणपत्र प्राप्त गर्नुहोस्",
            description="Once verified, OCR issues the certificate of incorporation electronically through CAMIS.",
            description_np="प्रमाणित भएपछि, OCR ले CAMIS मार्फत विद्युतीय रूपमा स्थापना प्रमाणपत्र जारी गर्छ।",
        )

        ProcessRequirement.objects.create(
            process=process, order=1, name="Promoters' citizenship certificates",
            name_np="प्रवर्द्धकहरूको नागरिकता प्रमाणपत्र",
            description="Copy of citizenship certificate for each promoter (or company registration certificate/passport for corporate/foreign promoters).",
            description_np="प्रत्येक प्रवर्द्धकको नागरिकता प्रमाणपत्रको प्रतिलिपि (वा संस्थागत/विदेशी प्रवर्द्धकको लागि कम्पनी दर्ता प्रमाणपत्र/राहदानी)।",
        )
        ProcessRequirement.objects.create(
            process=process, order=2, name="Memorandum of Association (MOA)", name_np="प्रबन्धपत्र (MOA)"
        )
        ProcessRequirement.objects.create(
            process=process, order=3, name="Articles of Association (AOA)", name_np="नियमावली (AOA)"
        )
        ProcessRequirement.objects.create(
            process=process, order=4, name="Reserved company name approval", name_np="आरक्षित कम्पनी नाम स्वीकृति"
        )
        ProcessRequirement.objects.create(
            process=process, order=5, name="Registered office address proof",
            name_np="दर्ता कार्यालयको ठेगाना प्रमाण", is_mandatory=False,
        )

        ProcessFAQ.objects.create(
            process=process, order=1,
            question="Do I need to visit the OCR office in person?",
            question_np="के मैले OCR कार्यालयमा स्वयं जानुपर्छ?",
            answer=(
                "Generally no - registration is completed online through the CAMIS portal. "
                "An in-person visit may be needed only for specific document verification or complex cases."
            ),
            answer_np=(
                "सामान्यतया पर्दैन - दर्ता CAMIS पोर्टलमार्फत अनलाइन पूरा हुन्छ। विशेष कागजात प्रमाणीकरण वा "
                "जटिल अवस्थाको हकमा मात्र स्वयं जानुपर्न सक्छ।"
            ),
        )
        ProcessFAQ.objects.create(
            process=process, order=2,
            question="How is the registration fee calculated?",
            question_np="दर्ता शुल्क कसरी गणना गरिन्छ?",
            answer=(
                "It is tiered by the company's authorized capital - ranging from NPR 1,000 for "
                "capital up to NPR 1 lakh, escalating to NPR 43,000+ for larger private companies. "
                "See the official fee schedule for exact tiers."
            ),
            answer_np=(
                "यो कम्पनीको अधिकृत पूँजीको आधारमा तहगत हुन्छ - १ लाखसम्मको पूँजीको लागि NPR १,००० देखि ठूला "
                "प्राइभेट कम्पनीका लागि NPR ४३,०००+ सम्म बढ्दै जान्छ। ठ्याक्कै दरका लागि आधिकारिक शुल्क तालिका हेर्नुहोस्।"
            ),
        )

        ProcessSource.objects.create(
            process=process, title="Office of the Company Registrar - official website",
            url="https://ocr.gov.np/", organization=org, last_verified_date=TODAY,
            notes="Registration process and CAMIS portal confirmed live on this date.",
        )
        ProcessSource.objects.create(
            process=process, title="OCR - Revenue / fee schedule",
            url="https://ocr.gov.np/pages/revenue/", organization=org, last_verified_date=TODAY,
            notes="Tiered registration fee schedule by authorized capital, fetched directly from this page.",
        )

        services.publish_new_version(
            process, publisher, changelog="Initial published version, seeded from official OCR sources."
        )
        return True

    def _seed_pan_registration(self, category, org, office, publisher):
        process, created = Process.objects.get_or_create(
            slug="register-for-a-pan",
            defaults={
                "title": "Register for a PAN (Permanent Account Number)",
                "title_np": "PAN (स्थायी लेखा नम्बर) को लागि दर्ता गर्नुहोस्",
                "category": category,
                "responsible_organization": org,
                "summary": (
                    "Get a PAN from the Inland Revenue Department - required for tax filing, "
                    "opening a business bank account, and most formal business activity in Nepal."
                ),
                "summary_np": (
                    "आन्तरिक राजस्व विभागबाट PAN प्राप्त गर्नुहोस् - कर तिर्न, व्यवसायिक बैंक खाता खोल्न, र "
                    "नेपालमा अधिकांश औपचारिक व्यावसायिक क्रियाकलापका लागि आवश्यक।"
                ),
                "description": (
                    "A PAN (Permanent Account Number) is issued free of charge by the Inland "
                    "Revenue Department (IRD) and is required to file taxes, register a business, "
                    "or open certain bank accounts in Nepal. Individuals can register online and "
                    "complete a one-time biometric verification at an IRD office; businesses "
                    "register with their business registration documents."
                ),
                "description_np": (
                    "PAN (स्थायी लेखा नम्बर) आन्तरिक राजस्व विभाग (IRD) ले निःशुल्क जारी गर्छ र नेपालमा कर "
                    "तिर्न, व्यवसाय दर्ता गर्न, वा केही बैंक खाता खोल्न आवश्यक हुन्छ। व्यक्तिले अनलाइन दर्ता गरी "
                    "IRD कार्यालयमा एकपटक बायोमेट्रिक प्रमाणीकरण पूरा गर्न सक्छन्; व्यवसायले आफ्ना दर्ता "
                    "कागजातहरूसहित दर्ता गर्छन्।"
                ),
                "eligibility": (
                    "Any Nepali citizen, foreign national, or registered business/organization "
                    "that needs to transact with Nepal's tax system."
                ),
                "eligibility_np": (
                    "नेपालको कर प्रणालीसँग कारोबार गर्नुपर्ने कुनै पनि नेपाली नागरिक, विदेशी नागरिक, वा दर्ता "
                    "भएको व्यवसाय/संस्था।"
                ),
                "estimated_duration_min_days": 1,
                "estimated_duration_max_days": 3,
                "total_fee_note": "Free - no registration fee.",
                "total_fee_note_np": "निःशुल्क - कुनै दर्ता शुल्क लाग्दैन।",
                "meta_title": "How to Register for a PAN in Nepal",
                "meta_title_np": "नेपालमा PAN को लागि कसरी दर्ता गर्ने",
                "meta_description": (
                    "How to get a PAN (Permanent Account Number) from Nepal's Inland Revenue "
                    "Department - free, online, individual or business."
                ),
                "meta_description_np": (
                    "नेपालको आन्तरिक राजस्व विभागबाट PAN (स्थायी लेखा नम्बर) कसरी प्राप्त गर्ने - निःशुल्क, "
                    "अनलाइन, व्यक्तिगत वा व्यवसायिक।"
                ),
            },
        )
        if not created:
            return False

        ProcessStep.objects.create(
            process=process, order=1, title="Apply online",
            title_np="अनलाइन आवेदन दिनुहोस्",
            description="Submit your PAN application at taxpayerportal.ird.gov.np, via the Nagarik app, or in person at your local IRD office.",
            description_np="taxpayerportal.ird.gov.np मा, नागरिक एपमार्फत, वा आफ्नो स्थानीय IRD कार्यालयमा गई आफ्नो PAN आवेदन पेश गर्नुहोस्।",
        )
        ProcessStep.objects.create(
            process=process, order=2, title="Complete biometric verification",
            title_np="बायोमेट्रिक प्रमाणीकरण पूरा गर्नुहोस्",
            description="Individuals complete a one-time biometric verification in person at an IRD office to finalize registration.",
            description_np="व्यक्तिले दर्ता अन्तिम रूप दिन IRD कार्यालयमा एकपटक स्वयं गई बायोमेट्रिक प्रमाणीकरण पूरा गर्नुपर्छ।",
            office=office, variant=ProcessVariant.INDIVIDUAL,
        )
        ProcessStep.objects.create(
            process=process, order=3, title="Submit business documents",
            title_np="व्यावसायिक कागजातहरू पेश गर्नुहोस्",
            description="Businesses submit their registration certificate and proprietor/partner PAN details for verification.",
            description_np="व्यवसायले प्रमाणीकरणका लागि आफ्नो दर्ता प्रमाणपत्र र मालिक/साझेदारको PAN विवरण पेश गर्छन्।",
            office=office, variant=ProcessVariant.BUSINESS,
        )
        ProcessStep.objects.create(
            process=process, order=4, title="Receive your PAN",
            title_np="आफ्नो PAN प्राप्त गर्नुहोस्",
            description="Once verified, IRD issues the PAN through its electronic system.",
            description_np="प्रमाणित भएपछि, IRD ले आफ्नो विद्युतीय प्रणालीमार्फत PAN जारी गर्छ।",
        )

        ProcessRequirement.objects.create(
            process=process, order=1, name="Citizenship certificate", name_np="नागरिकता प्रमाणपत्र",
            variant=ProcessVariant.INDIVIDUAL,
        )
        ProcessRequirement.objects.create(
            process=process, order=2, name="Recent photograph, email address, and mobile number",
            name_np="हालसालैको फोटो, इमेल ठेगाना, र मोबाइल नम्बर",
            variant=ProcessVariant.INDIVIDUAL,
        )
        ProcessRequirement.objects.create(
            process=process, order=3, name="Business registration certificate",
            name_np="व्यवसाय दर्ता प्रमाणपत्र", variant=ProcessVariant.BUSINESS,
        )
        ProcessRequirement.objects.create(
            process=process, order=4, name="Proprietor/partner PAN or citizenship details",
            name_np="मालिक/साझेदारको PAN वा नागरिकता विवरण",
            variant=ProcessVariant.BUSINESS,
        )
        ProcessRequirement.objects.create(
            process=process, order=5, name="Passport, visa, and work permit (foreign nationals only)",
            name_np="राहदानी, भिसा, र कामको अनुमतिपत्र (विदेशी नागरिकका लागि मात्र)",
            is_mandatory=False,
        )

        ProcessFAQ.objects.create(
            process=process, order=1,
            question="Is there a fee for PAN registration?",
            question_np="PAN दर्ताको लागि शुल्क लाग्छ?",
            answer="No - PAN registration is free of charge.",
            answer_np="छैन - PAN दर्ता निःशुल्क छ।",
        )
        ProcessFAQ.objects.create(
            process=process, order=2,
            question="Do I need to visit an IRD office?",
            question_np="मैले IRD कार्यालयमा जानुपर्छ?",
            answer=(
                "Individuals apply online but must complete a one-time in-person biometric "
                "verification. Businesses can often complete registration without a biometric visit."
            ),
            answer_np=(
                "व्यक्तिले अनलाइन आवेदन दिन्छन् तर एकपटक स्वयं गई बायोमेट्रिक प्रमाणीकरण पूरा गर्नुपर्छ। "
                "व्यवसायले प्रायः बायोमेट्रिक भ्रमणविना दर्ता पूरा गर्न सक्छन्।"
            ),
        )

        ProcessSource.objects.create(
            process=process, title="Inland Revenue Department - official website",
            url="https://ird.gov.np/", organization=org, last_verified_date=TODAY,
            notes=(
                "Confirmed PAN search/registration services live on this date; the fee-free "
                "status is corroborated by independent professional sources since no fee "
                "schedule for PAN registration appears on the department's own site."
            ),
        )

        services.publish_new_version(
            process, publisher, changelog="Initial published version, seeded from official IRD sources."
        )
        return True

    def _seed_passport(self, category, org, office, publisher):
        process, created = Process.objects.get_or_create(
            slug="apply-for-a-nepali-passport",
            defaults={
                "title": "Apply for a Nepali Passport",
                "title_np": "नेपाली राहदानीको लागि आवेदन दिनुहोस्",
                "category": category,
                "responsible_organization": org,
                "summary": (
                    "Passport application in Nepal: apply for a new Nepali e-passport or renew "
                    "an existing one through the Department of Passports."
                ),
                "summary_np": (
                    "राहदानी विभागमार्फत नयाँ नेपाली ई-राहदानीको लागि आवेदन दिनुहोस् वा भइरहेको राहदानी "
                    "नवीकरण गर्नुहोस्।"
                ),
                "description": (
                    "Nepali citizens apply for an e-passport through online pre-enrollment "
                    "followed by biometric registration and document verification. The regular "
                    "process is handled through District Administration Offices (10-30 working "
                    "days); an expedited service is available directly at the Department of "
                    "Passports in Tripureshwor, Kathmandu (around 2 working days, for an "
                    "additional fee)."
                ),
                "description_np": (
                    "नेपाली नागरिकहरूले अनलाइन पूर्व-दर्ता पछि बायोमेट्रिक दर्ता र कागजात प्रमाणीकरणमार्फत "
                    "ई-राहदानीको लागि आवेदन दिन्छन्। नियमित प्रक्रिया जिल्ला प्रशासन कार्यालयहरूमार्फत हुन्छ "
                    "(१०-३० कार्यदिन); त्रिपुरेश्वर, काठमाडौंस्थित राहदानी विभागमा सिधै गई द्रुत सेवा पनि "
                    "उपलब्ध छ (लगभग २ कार्यदिन, थप शुल्कसहित)।"
                ),
                "eligibility": (
                    "Nepali citizens holding a valid citizenship certificate (or, for minors, "
                    "a minor identification card)."
                ),
                "eligibility_np": (
                    "मान्य नागरिकता प्रमाणपत्र भएका नेपाली नागरिकहरू (वा नाबालकका लागि, नाबालक परिचयपत्र)।"
                ),
                "estimated_duration_min_days": 10,
                "estimated_duration_max_days": 30,
                "estimated_duration_note": (
                    "10-30 days via regular District Administration Office processing; "
                    "~2 working days for expedited service at the Department of Passports "
                    "HQ (additional fee applies)."
                ),
                "estimated_duration_note_np": (
                    "नियमित जिल्ला प्रशासन कार्यालय प्रक्रियामार्फत १०-३० दिन; राहदानी विभागको मुख्यालयमा "
                    "द्रुत सेवाको लागि लगभग २ कार्यदिन (थप शुल्क लाग्छ)।"
                ),
                "total_fee_note": (
                    "NPR 12,000 (34-page) / NPR 20,000 (66-page) for new/renewal adults; "
                    "other tiers apply for lost/damaged passports, children, and expedited service."
                ),
                "total_fee_note_np": (
                    "नयाँ/नवीकरण वयस्कका लागि NPR १२,००० (३४-पृष्ठ) / NPR २०,००० (६६-पृष्ठ); हराएको/बिग्रेको "
                    "राहदानी, बालबालिका, र द्रुत सेवाको लागि फरक-फरक दर लाग्छ।"
                ),
                "meta_title": "How to Apply for a Nepali Passport",
                "meta_title_np": "नेपाली राहदानीको लागि कसरी आवेदन दिने",
                "meta_description": (
                    "Step-by-step guide to applying for or renewing a Nepali e-passport through "
                    "the Department of Passports, with official fees and required documents."
                ),
                "meta_description_np": (
                    "राहदानी विभागमार्फत नेपाली ई-राहदानीको लागि आवेदन दिने वा नवीकरण गर्ने चरणबद्ध "
                    "मार्गदर्शन, आधिकारिक शुल्क र आवश्यक कागजातहरूसहित।"
                ),
            },
        )
        if not created:
            return False

        ProcessStep.objects.create(
            process=process, order=1, title="Complete online pre-enrollment",
            title_np="अनलाइन पूर्व-दर्ता पूरा गर्नुहोस्",
            description="Create an account and complete pre-enrollment at nepalpassport.gov.np using your citizenship number and mobile number.",
            description_np="आफ्नो नागरिकता नम्बर र मोबाइल नम्बर प्रयोग गरी nepalpassport.gov.np मा खाता बनाई पूर्व-दर्ता पूरा गर्नुहोस्।",
        )
        ProcessStep.objects.create(
            process=process, order=2, title="Visit a District Administration Office or the Department HQ",
            title_np="जिल्ला प्रशासन कार्यालय वा विभागको मुख्यालय जानुहोस्",
            description=(
                "For regular service, visit the District/Sub-district Administration Office "
                "that issued your citizenship certificate. For expedited service (~2 working "
                "days), visit the Department of Passports HQ in Tripureshwor, Kathmandu directly."
            ),
            description_np=(
                "नियमित सेवाका लागि, आफ्नो नागरिकता प्रमाणपत्र जारी गर्ने जिल्ला/उपजिल्ला प्रशासन कार्यालयमा "
                "जानुहोस्। द्रुत सेवाका लागि (लगभग २ कार्यदिन), त्रिपुरेश्वर, काठमाडौंस्थित राहदानी विभागको "
                "मुख्यालयमा सिधै जानुहोस्।"
            ),
            office=office,
        )
        ProcessStep.objects.create(
            process=process, order=3, title="Submit documents and biometrics",
            title_np="कागजात र बायोमेट्रिक पेश गर्नुहोस्",
            description="Submit your printed pre-enrollment form, citizenship certificate, and (for renewals) previous passport, then complete photo and biometric capture.",
            description_np="आफ्नो मुद्रित पूर्व-दर्ता फारम, नागरिकता प्रमाणपत्र, र (नवीकरणको लागि) अघिल्लो राहदानी पेश गरी फोटो र बायोमेट्रिक खिच्ने काम पूरा गर्नुहोस्।",
        )
        ProcessStep.objects.create(
            process=process, order=4, title="Pay the passport fee",
            title_np="राहदानी शुल्क बुझाउनुहोस्",
            description="Pay the fee for your passport type (page count, new/renewal vs lost/damaged, adult vs child) at the office or via bank voucher.",
            description_np="आफ्नो राहदानी प्रकार (पृष्ठ संख्या, नयाँ/नवीकरण वा हराएको/बिग्रेको) अनुसारको शुल्क कार्यालयमा वा बैंक भौचरमार्फत बुझाउनुहोस्।",
            fee_note="NPR 12,000-25,000 depending on page count, category, and whether it is new/renewal or a replacement.",
            fee_note_np="पृष्ठ संख्या, वर्ग, र नयाँ/नवीकरण वा प्रतिस्थापन अनुसार NPR १२,०००-२५,०००।",
        )
        ProcessStep.objects.create(
            process=process, order=5, title="Collect your passport",
            title_np="आफ्नो राहदानी बुझ्नुहोस्",
            description="Collect your passport once ready, or as instructed by the office (regular: 10-30 days; expedited: ~2 working days).",
            description_np="तयार भएपछि वा कार्यालयले तोकेबमोजिम आफ्नो राहदानी बुझ्नुहोस् (नियमित: १०-३० दिन; द्रुत: लगभग २ कार्यदिन)।",
        )

        ProcessRequirement.objects.create(
            process=process, order=1, name="Citizenship certificate (original + photocopy)",
            name_np="नागरिकता प्रमाणपत्र (सक्कल + प्रतिलिपि)",
        )
        ProcessRequirement.objects.create(
            process=process, order=2, name="Printed pre-enrollment form with barcode/QR code",
            name_np="बारकोड/QR कोड सहितको मुद्रित पूर्व-दर्ता फारम",
        )
        ProcessRequirement.objects.create(
            process=process, order=3, name="Previous passport (photocopy)", name_np="अघिल्लो राहदानी (प्रतिलिपि)",
            is_mandatory=False,
            description="Required for renewals only.", description_np="नवीकरणका लागि मात्र आवश्यक।",
        )
        ProcessRequirement.objects.create(
            process=process, order=4, name="Both parents' citizenship certificates and marriage registration certificate",
            name_np="दुवै अभिभावकको नागरिकता प्रमाणपत्र र विवाह दर्ता प्रमाणपत्र",
            is_mandatory=False, description="Required for minor applicants only.",
            description_np="नाबालक आवेदकका लागि मात्र आवश्यक।",
        )
        ProcessRequirement.objects.create(
            process=process, order=5, name="Payment receipt / bank voucher",
            name_np="भुक्तानी रसिद / बैंक भौचर",
        )

        ProcessFAQ.objects.create(
            process=process, order=1,
            question="How much does a Nepali passport cost?",
            question_np="नेपाली राहदानीको मूल्य कति हो?",
            answer=(
                "NPR 12,000 for a 34-page passport or NPR 20,000 for a 66-page passport, for a "
                "new/renewal adult application processed within Nepal. Lost/damaged replacements "
                "and child passports have different fee tiers - check the official fee schedule "
                "for your exact category."
            ),
            answer_np=(
                "नेपालभित्र प्रशोधन हुने नयाँ/नवीकरण वयस्क आवेदनको लागि ३४-पृष्ठे राहदानीको NPR १२,००० वा "
                "६६-पृष्ठेको NPR २०,०००। हराएको/बिग्रेको प्रतिस्थापन र बालबालिकाको राहदानीको फरक-फरक दर "
                "लाग्छ - आफ्नो वर्गको लागि आधिकारिक शुल्क तालिका जाँच्नुहोस्।"
            ),
        )
        ProcessFAQ.objects.create(
            process=process, order=2,
            question="How long does it take?",
            question_np="यसमा कति समय लाग्छ?",
            answer=(
                "10-30 working days through the regular District Administration Office process, "
                "or around 2 working days if applying directly at the Department of Passports "
                "headquarters in Kathmandu (for an additional fee)."
            ),
            answer_np=(
                "नियमित जिल्ला प्रशासन कार्यालय प्रक्रियामार्फत १०-३० कार्यदिन, वा काठमाडौंस्थित राहदानी "
                "विभागको मुख्यालयमा सिधै आवेदन दिए लगभग २ कार्यदिन (थप शुल्कसहित)।"
            ),
        )

        ProcessSource.objects.create(
            process=process, title="Department of Passports - official website",
            url="https://nepalpassport.gov.np/", organization=org, last_verified_date=TODAY,
        )
        ProcessSource.objects.create(
            process=process, title="Department of Passports - fee schedule",
            url="https://nepalpassport.gov.np/process/-41", organization=org, last_verified_date=TODAY,
            notes=(
                "Fee figures fetched directly from this official page. Several third-party "
                "sources reported different (lower) figures for 'normal' processing - this "
                "platform follows the primary government source rather than the aggregator "
                "consensus, per its own trust policy."
            ),
        )
        ProcessSource.objects.create(
            process=process, title="Department of Passports - application process (within Nepal)",
            url="https://nepalpassport.gov.np/process/-1", organization=org, last_verified_date=TODAY,
        )

        services.publish_new_version(
            process, publisher, changelog="Initial published version, seeded from official Department of Passports sources."
        )
        return True
