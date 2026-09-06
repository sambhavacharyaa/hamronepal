from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tourism.models import Destination, DestinationCategory, DestinationHighlight, Season

TODAY = date.today()


class Command(BaseCommand):
    help = (
        "Seed six real, source-cited flagship destinations (Kathmandu Valley, Pokhara, "
        "Chitwan National Park, the Everest/Khumbu region, Lumbini, Rara Lake), "
        "researched and fact-checked against Wikipedia."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        heritage, _ = DestinationCategory.objects.get_or_create(
            slug="heritage-culture",
            defaults={"name": "Heritage & Culture", "name_np": "सम्पदा र संस्कृति", "order": 1},
        )
        nature, _ = DestinationCategory.objects.get_or_create(
            slug="nature-wildlife",
            defaults={"name": "Nature & Wildlife", "name_np": "प्रकृति र वन्यजन्तु", "order": 2},
        )
        adventure, _ = DestinationCategory.objects.get_or_create(
            slug="adventure-trekking",
            defaults={"name": "Adventure & Trekking", "name_np": "साहसिक यात्रा र पदयात्रा", "order": 3},
        )
        lakes, _ = DestinationCategory.objects.get_or_create(
            slug="lakes-valleys",
            defaults={"name": "Lakes & Valleys", "name_np": "ताल र उपत्यका", "order": 4},
        )
        spiritual, _ = DestinationCategory.objects.get_or_create(
            slug="spiritual-pilgrimage",
            defaults={"name": "Spiritual & Pilgrimage", "name_np": "आध्यात्मिक र तीर्थयात्रा", "order": 5},
        )

        created_count = 0
        created_count += self._seed_kathmandu_valley(heritage)
        created_count += self._seed_pokhara(lakes)
        created_count += self._seed_chitwan(nature)
        created_count += self._seed_everest(adventure)
        created_count += self._seed_lumbini(spiritual)
        created_count += self._seed_rara_lake(nature)

        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} new destination(s)."))

    def _seed_kathmandu_valley(self, category):
        destination, created = Destination.objects.get_or_create(
            slug="kathmandu-valley",
            defaults={
                "title": "Kathmandu Valley",
                "title_np": "काठमाडौं उपत्यका",
                "category": category,
                "region": "Kathmandu Valley",
                "summary": (
                    "Nepal's cultural heart: seven UNESCO World Heritage monument zones packed "
                    "into one valley, from royal squares to ancient stupas."
                ),
                "summary_np": (
                    "नेपालको सांस्कृतिक हृदय: एउटै उपत्यकामा सातवटा युनेस्को विश्व सम्पदा क्षेत्रहरू।"
                ),
                "description": (
                    "The Kathmandu Valley was inscribed as a UNESCO World Heritage Site in 1979, "
                    "covering seven monument zones: Kathmandu Durbar Square, Patan Durbar Square, "
                    "Bhaktapur Durbar Square, Swayambhunath, Boudhanath, Pashupatinath, and Changu "
                    "Narayan Temple. Each site can realistically be visited on its own half-day trip, "
                    "so most travelers base themselves in Kathmandu or Patan and move between them."
                ),
                "description_np": (
                    "काठमाडौं उपत्यका सन् १९७९ मा युनेस्को विश्व सम्पदा सूचीमा सूचीकृत भएको थियो, जसमा "
                    "सात वटा स्मारक क्षेत्रहरू समावेश छन्।"
                ),
                "highlights_intro": "Things to do in the valley",
                "highlights_intro_np": "उपत्यकामा गर्न सकिने कुराहरू",
                "best_season": Season.AUTUMN,
                "budget_note": "Budget stays from NPR 1,500/night; heritage site entry fees are separate and vary by site.",
                "budget_note_np": "बजेट बसाइ रात्रि NPR १,५०० देखि सुरु हुन्छ।",
                "status": Destination.Status.PUBLISHED,
                "source_url": "https://en.wikipedia.org/wiki/Kathmandu_Valley",
                "source_note": "Wikipedia, cross-checked against the UNESCO monument zone list",
                "last_verified_at": TODAY,
                "meta_title": "Kathmandu Valley Travel Guide",
                "meta_title_np": "काठमाडौं उपत्यका यात्रा गाइड",
                "meta_description": "Plan a trip to the Kathmandu Valley's seven UNESCO World Heritage sites.",
                "meta_description_np": "काठमाडौं उपत्यकाको सातवटा युनेस्को विश्व सम्पदा स्थलहरूको यात्रा योजना बनाउनुहोस्।",
            },
        )
        if not created:
            return 0
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Walk Kathmandu Durbar Square at dawn",
            title_np="बिहान सबेरै काठमाडौं दरबार क्षेत्र घुम्नुहोस्",
            description="Before the crowds arrive, when the temple bells and pigeons have the square to themselves.",
            order=1,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Circle Boudhanath Stupa",
            title_np="बौद्धनाथ स्तूप परिक्रमा गर्नुहोस्",
            description="One of the largest stupas in the world, and a living center of Tibetan Buddhist life in the city.",
            order=2,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.TRANSPORT,
            title="Getting between the durbar squares",
            title_np="दरबार क्षेत्रहरू बीच ओहोरदोहोर",
            description="Kathmandu, Patan, and Bhaktapur durbar squares are each a short taxi or local bus ride apart.",
            order=1,
        )
        return 1

    def _seed_pokhara(self, category):
        destination, created = Destination.objects.get_or_create(
            slug="pokhara",
            defaults={
                "title": "Pokhara",
                "title_np": "पोखरा",
                "category": category,
                "region": "Pokhara Valley",
                "summary": (
                    "Nepal's tourism capital, built around Phewa Lake, with three of the world's "
                    "ten highest peaks visible from the valley floor."
                ),
                "summary_np": "फेवा तालको वरिपरि बसेको नेपालको पर्यटन राजधानी।",
                "description": (
                    "Pokhara sits at an average elevation of about 822 meters, on the shore of "
                    "Phewa Lake. It's the standard starting point for the Annapurna Circuit and "
                    "Annapurna Base Camp treks, and Sarangkot hill above the city is one of the "
                    "most accessible paragliding and sunrise-viewpoint spots in the country."
                ),
                "description_np": (
                    "पोखरा समुद्री सतहबाट औसत ८२२ मिटर उचाइमा, फेवा तालको किनारमा अवस्थित छ।"
                ),
                "highlights_intro": "Things to do around the lake",
                "highlights_intro_np": "तालको वरिपरि गर्न सकिने कुराहरू",
                "best_season": Season.AUTUMN,
                "budget_note": "Lakeside guesthouses from NPR 1,200/night; a tandem paraglide typically runs USD 80-100.",
                "budget_note_np": "तालकिनारका गेस्टहाउस रात्रि NPR १,२०० देखि सुरु हुन्छ।",
                "status": Destination.Status.PUBLISHED,
                "source_url": "https://en.wikipedia.org/wiki/Pokhara",
                "source_note": "Wikipedia",
                "last_verified_at": TODAY,
                "meta_title": "Pokhara Travel Guide",
                "meta_title_np": "पोखरा यात्रा गाइड",
                "meta_description": "Phewa Lake, Sarangkot sunrise, and the gateway to the Annapurna treks.",
                "meta_description_np": "फेवा ताल, सारंकोट सूर्योदय, र अन्नपूर्ण पदयात्राको प्रवेशद्वार।",
            },
        )
        if not created:
            return 0
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Sunrise at Sarangkot",
            title_np="सारंकोटमा सूर्योदय",
            description="A short drive or hike above the city for a panoramic Annapurna and Machhapuchhre view.",
            order=1,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Row out on Phewa Lake",
            title_np="फेवा तालमा डुंगा चलाउनुहोस्",
            description="Rent a wooden boat out to the Tal Barahi temple island in the middle of the lake.",
            order=2,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.STAY,
            title="Lakeside (Baidam)",
            title_np="लेकसाइड (बैदाम)",
            description="The main tourist strip along Phewa Lake, with the widest range of guesthouses and restaurants.",
            order=1,
        )
        return 1

    def _seed_chitwan(self, category):
        destination, created = Destination.objects.get_or_create(
            slug="chitwan-national-park",
            defaults={
                "title": "Chitwan National Park",
                "title_np": "चितवन राष्ट्रिय निकुञ्ज",
                "category": category,
                "region": "Chitwan, Terai",
                "summary": (
                    "Nepal's first national park, and a UNESCO World Heritage Site since 1984, "
                    "home to one-horned rhinoceros and Bengal tigers in the lowland Terai."
                ),
                "summary_np": "नेपालको पहिलो राष्ट्रिय निकुञ्ज, गैंडा र बाघको बासस्थान।",
                "description": (
                    "Established in 1973 as Nepal's first national park and inscribed by UNESCO "
                    "in 1984, Chitwan covers roughly 953 square kilometers of the Terai lowlands. "
                    "Its rhinoceros population has recovered significantly since the park's early "
                    "years, and it remains one of the best places in Asia for a real chance at "
                    "seeing a wild Bengal tiger, alongside gharial crocodiles and over 500 bird species."
                ),
                "description_np": (
                    "सन् १९७३ मा स्थापना भएको र सन् १९८४ मा युनेस्कोद्वारा सूचीकृत, चितवनले तराईको "
                    "करिब ९५३ वर्ग किलोमिटर क्षेत्र ओगटेको छ।"
                ),
                "highlights_intro": "Things to do in the park",
                "highlights_intro_np": "निकुञ्जमा गर्न सकिने कुराहरू",
                "best_season": Season.WINTER,
                "budget_note": "Park entry plus a guided jeep safari typically runs USD 40-60 per person.",
                "budget_note_np": "निकुञ्ज प्रवेश र गाइडेड जीप सफारी प्रति व्यक्ति USD ४०-६० हुन्छ।",
                "status": Destination.Status.PUBLISHED,
                "source_url": "https://en.wikipedia.org/wiki/Chitwan_National_Park",
                "source_note": "Wikipedia",
                "last_verified_at": TODAY,
                "meta_title": "Chitwan National Park Travel Guide",
                "meta_title_np": "चितवन राष्ट्रिय निकुञ्ज यात्रा गाइड",
                "meta_description": "Wildlife safaris in Nepal's first national park, home to rhinos and Bengal tigers.",
                "meta_description_np": "नेपालको पहिलो राष्ट्रिय निकुञ्जमा वन्यजन्तु सफारी।",
            },
        )
        if not created:
            return 0
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Jeep safari for rhino and tiger",
            title_np="गैंडा र बाघको लागि जीप सफारी",
            description="Guided jeep safaris run early morning and late afternoon, when wildlife is most active.",
            order=1,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Canoe ride on the Rapti River",
            title_np="राप्ती नदीमा डुंगा यात्रा",
            description="A quiet dugout-canoe float past gharial crocodiles and riverbank birdlife.",
            order=2,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.TRANSPORT,
            title="Getting to Chitwan",
            title_np="चितवन कसरी पुग्ने",
            description="Around 5-6 hours by road from Kathmandu, or a short domestic flight to Bharatpur.",
            order=1,
        )
        return 1

    def _seed_everest(self, category):
        destination, created = Destination.objects.get_or_create(
            slug="everest-khumbu-region",
            defaults={
                "title": "Everest / Khumbu Region",
                "title_np": "एभरेस्ट / खुम्बु क्षेत्र",
                "category": category,
                "region": "Khumbu, Solukhumbu District",
                "summary": (
                    "Sagarmatha National Park, a UNESCO World Heritage Site since 1979, "
                    "spanning 2,845 to 8,848 meters and home to the Everest Base Camp trek "
                    "and Sherpa mountain villages."
                ),
                "summary_np": "सगरमाथा राष्ट्रिय निकुञ्ज, एभरेस्ट बेस क्याम्प पदयात्राको घर।",
                "description": (
                    "Sagarmatha National Park was Nepal's first natural site inscribed by "
                    "UNESCO, in 1979. It ranges from 2,845 meters up to the summit of Everest "
                    "at 8,848 meters, and around 3,500 Sherpa people live in villages and "
                    "seasonal settlements along the main trekking trails. Most visitors fly "
                    "into Lukla and trek up the Khumbu valley toward Everest Base Camp over "
                    "1-2 weeks, acclimatizing as they go."
                ),
                "description_np": (
                    "सगरमाथा राष्ट्रिय निकुञ्ज सन् १९७९ मा युनेस्कोद्वारा सूचीकृत नेपालको पहिलो प्राकृतिक "
                    "सम्पदा स्थल हो।"
                ),
                "highlights_intro": "Things to plan for",
                "highlights_intro_np": "योजना बनाउनुपर्ने कुराहरू",
                "best_season": Season.AUTUMN,
                "budget_note": "A guided Everest Base Camp trek typically runs USD 1,200-2,500 depending on services included.",
                "budget_note_np": "गाइडेड एभरेस्ट बेस क्याम्प पदयात्रा सामान्यतया USD १,२००-२,५०० हुन्छ।",
                "status": Destination.Status.PUBLISHED,
                "source_url": "https://en.wikipedia.org/wiki/Sagarmatha_National_Park",
                "source_note": "Wikipedia",
                "last_verified_at": TODAY,
                "meta_title": "Everest / Khumbu Region Trekking Guide",
                "meta_title_np": "एभरेस्ट / खुम्बु क्षेत्र पदयात्रा गाइड",
                "meta_description": "Plan an Everest Base Camp trek through Sagarmatha National Park and Sherpa villages.",
                "meta_description_np": "सगरमाथा राष्ट्रिय निकुञ्ज हुँदै एभरेस्ट बेस क्याम्प पदयात्रा योजना।",
            },
        )
        if not created:
            return 0
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Trek to Everest Base Camp",
            title_np="एभरेस्ट बेस क्याम्पसम्म पदयात्रा",
            description="A multi-day trek up the Khumbu valley, with acclimatization days built in along the way.",
            order=1,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.TRANSPORT,
            title="Fly into Lukla",
            title_np="लुक्ला उडान",
            description="The standard approach is a short mountain flight from Kathmandu to Lukla's Tenzing-Hillary Airport.",
            order=1,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.STAY,
            title="Teahouses along the trail",
            title_np="बाटोमा टीहाउसहरू",
            description="Sherpa-run teahouses in Namche Bazaar, Tengboche, and Dingboche provide beds and meals along the route.",
            order=1,
        )
        return 1

    def _seed_lumbini(self, category):
        destination, created = Destination.objects.get_or_create(
            slug="lumbini",
            defaults={
                "title": "Lumbini",
                "title_np": "लुम्बिनी",
                "category": category,
                "region": "Lumbini, Terai",
                "summary": (
                    "The birthplace of Siddhartha Gautama, the Buddha, and a UNESCO World "
                    "Heritage Site since 1997, centered on the Maya Devi Temple."
                ),
                "summary_np": "गौतम बुद्धको जन्मस्थल, सन् १९९७ देखि युनेस्को विश्व सम्पदा स्थल।",
                "description": (
                    "According to Buddhist tradition, Queen Maya Devi gave birth to Siddhartha "
                    "Gautama in Lumbini around 563 BCE. The Maya Devi Temple marks the traditional "
                    "birthplace, and a nearby Ashoka Pillar, erected by Emperor Ashoka in the 3rd "
                    "century BCE and rediscovered in 1896, carries an inscription confirming the "
                    "site. Lumbini today is a quiet pilgrimage complex with monasteries built by "
                    "Buddhist communities from around the world."
                ),
                "description_np": (
                    "बौद्ध परम्परा अनुसार, रानी मायादेवीले लगभग ५६३ ईसा पूर्वमा लुम्बिनीमा सिद्धार्थ "
                    "गौतमलाई जन्म दिइन्।"
                ),
                "highlights_intro": "What to see in the complex",
                "highlights_intro_np": "परिसरमा हेर्न लायक कुराहरू",
                "best_season": Season.WINTER,
                "budget_note": "A day trip is enough for most visitors; simple guesthouses near the complex from NPR 1,000/night.",
                "budget_note_np": "परिसर नजिकैका सामान्य गेस्टहाउस रात्रि NPR १,००० देखि सुरु हुन्छ।",
                "status": Destination.Status.PUBLISHED,
                "source_url": "https://en.wikipedia.org/wiki/Lumbini",
                "source_note": "Wikipedia",
                "last_verified_at": TODAY,
                "meta_title": "Lumbini Travel Guide",
                "meta_title_np": "लुम्बिनी यात्रा गाइड",
                "meta_description": "Visit the birthplace of the Buddha and the Maya Devi Temple in Lumbini.",
                "meta_description_np": "बुद्धको जन्मस्थल र मायादेवी मन्दिर भ्रमण गर्नुहोस्।",
            },
        )
        if not created:
            return 0
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Maya Devi Temple",
            title_np="मायादेवी मन्दिर",
            description="The marker stone and ancient ruins at the traditional birthplace site, inside the sacred garden.",
            order=1,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Ashoka Pillar",
            title_np="अशोक स्तम्भ",
            description="A 3rd-century BCE stone column with a Brahmi inscription confirming Lumbini as the Buddha's birthplace.",
            order=2,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Monastic Zone",
            title_np="विहार क्षेत्र",
            description="Monasteries built by Buddhist communities from different countries, each in their own architectural style.",
            order=3,
        )
        return 1

    def _seed_rara_lake(self, category):
        destination, created = Destination.objects.get_or_create(
            slug="rara-lake",
            defaults={
                "title": "Rara Lake",
                "title_np": "रारा ताल",
                "category": category,
                "region": "Mugu, Karnali Province",
                "summary": (
                    "Nepal's largest lake, at nearly 3,000 meters in the remote far west, "
                    "inside Rara National Park."
                ),
                "summary_np": "नेपालको सबैभन्दा ठूलो ताल, टाढाको पश्चिम क्षेत्रमा।",
                "description": (
                    "Rara Lake is the largest freshwater lake in the Nepalese Himalayas, sitting "
                    "at about 2,990 meters above sea level inside Rara National Park, spanning "
                    "Mugu and Jumla districts in Karnali Province. It covers roughly 10.6 square "
                    "kilometers and reaches depths of up to 167 meters. Far fewer visitors make "
                    "it out here than to Pokhara or the Everest region, largely because of how "
                    "remote it is, which is exactly why the ones who do tend to have it nearly to themselves."
                ),
                "description_np": (
                    "रारा ताल नेपाली हिमालको सबैभन्दा ठूलो मीठो पानीको ताल हो, जुन कर्णाली प्रदेशको "
                    "मुगु र जुम्ला जिल्लामा फैलिएको रारा राष्ट्रिय निकुञ्ज भित्र लगभग २,९९० मिटर उचाइमा अवस्थित छ।"
                ),
                "highlights_intro": "Things to do at the lake",
                "highlights_intro_np": "तालमा गर्न सकिने कुराहरू",
                "best_season": Season.AUTUMN,
                "budget_note": "Getting here usually means a domestic flight to Talcha or a multi-day trek; budget more than a typical trip.",
                "budget_note_np": "यहाँ पुग्न सामान्यतया तल्चा उडान वा बहु-दिने पदयात्रा आवश्यक पर्छ।",
                "status": Destination.Status.PUBLISHED,
                "source_url": "https://en.wikipedia.org/wiki/Rara_Lake",
                "source_note": "Wikipedia",
                "last_verified_at": TODAY,
                "meta_title": "Rara Lake Travel Guide",
                "meta_title_np": "रारा ताल यात्रा गाइड",
                "meta_description": "Nepal's largest lake, remote and rarely crowded, in the far-western Himalayas.",
                "meta_description_np": "नेपालको सबैभन्दा ठूलो ताल, टाढाको पश्चिमी हिमालमा।",
            },
        )
        if not created:
            return 0
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.ACTIVITY,
            title="Walk the lakeshore trail",
            title_np="तालको किनारको बाटो हिँड्नुहोस्",
            description="A gentle, mostly flat trail circles much of the lake through pine and blue pine forest.",
            order=1,
        )
        DestinationHighlight.objects.create(
            destination=destination,
            kind=DestinationHighlight.Kind.TRANSPORT,
            title="Fly to Talcha",
            title_np="तल्चा उडान",
            description="The fastest route is a domestic flight to Talcha Airport, followed by a short walk to the lake.",
            order=1,
        )
        return 1
