from django.core.management.base import BaseCommand
from apps.services.models import Service, ServiceCategory
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Load sample services data for Selangor'

    def handle(self, *args, **options):
        # Clear existing services (optional - remove if you want to keep existing data)
        Service.objects.all().delete()
        ServiceCategory.objects.all().delete()
        
        # Create categories
        categories = {
            'healthcare': ServiceCategory.objects.create(
                name='Healthcare',
                description='Medical services and health facilities'
            ),
            'food': ServiceCategory.objects.create(
                name='Food Services',
                description='Food assistance and nutrition programs'
            ),
            'shelter': ServiceCategory.objects.create(
                name='Shelter & Housing',
                description='Temporary housing and shelter services'
            ),
            'education': ServiceCategory.objects.create(
                name='Education',
                description='Educational resources and programs'
            ),
            'emergency': ServiceCategory.objects.create(
                name='Emergency Services',
                description='Emergency assistance and crisis support'
            ),
            'social': ServiceCategory.objects.create(
                name='Social Services',
                description='Community support and social programs'
            ),
        }

        # Sample services data
        services_data = [
            # Healthcare Services
            {
                'name': 'Hospital Kuala Lumpur',
                'category': categories['healthcare'],
                'description': 'Major public hospital providing comprehensive medical services including emergency care, specialist consultations, and surgical procedures. 24/7 emergency services available.',
                'address': 'Jalan Pahang, 53000 Kuala Lumpur, Wilayah Persekutuan',
                'phone': '+60-3-2615-5555',
                'latitude': 3.1725,
                'longitude': 101.7068,
                'current_capacity': 85,
                'max_capacity': 100,
                'current_status': 'open',
                'is_emergency_service': True,
            },
            {
                'name': 'Klinik Kesihatan Shah Alam',
                'category': categories['healthcare'],
                'description': 'Community health clinic offering primary healthcare services, maternal and child health programs, and preventive care for residents of Shah Alam.',
                'address': 'Seksyen 7, 40000 Shah Alam, Selangor',
                'phone': '+60-3-5519-6144',
                'latitude': 3.0738,
                'longitude': 101.5183,
                'current_capacity': 45,
                'max_capacity': 60,
                'current_status': 'open',
                'is_emergency_service': False,
            },
            {
                'name': 'Hospital Tengku Ampuan Rahimah',
                'category': categories['healthcare'],
                'description': 'Specialist hospital in Klang providing advanced medical care including cardiology, oncology, and pediatric services. Known for excellent patient care.',
                'address': 'Jalan Langat, 41200 Klang, Selangor',
                'phone': '+60-3-3375-7000',
                'latitude': 3.0319,
                'longitude': 101.4481,
                'current_capacity': 120,
                'max_capacity': 150,
                'current_status': 'limited',
                'is_emergency_service': True,
            },

            # Food Services
            {
                'name': 'Pertubuhan Kebajikan Makanan Selangor',
                'category': categories['food'],
                'description': 'Food bank providing free meals and groceries to low-income families. Daily hot meals served from 12pm-2pm and food packages available for families in need.',
                'address': 'Seksyen 14, 40000 Shah Alam, Selangor',
                'phone': '+60-3-5511-2233',
                'latitude': 3.0667,
                'longitude': 101.5167,
                'capacity_current': 200,
                'capacity_max': 300,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Dapur Ramadan Komuniti',
                'category': categories['food'],
                'description': 'Community kitchen serving free meals during Ramadan and year-round food assistance. Volunteers welcome. Special programs for elderly and disabled residents.',
                'address': 'Taman Megah, 47301 Petaling Jaya, Selangor',
                'phone': '+60-3-7957-4466',
                'latitude': 3.1048,
                'longitude': 101.6395,
                'capacity_current': 150,
                'capacity_max': 250,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Pusat Makanan Amal Subang',
                'category': categories['food'],
                'description': 'Charitable food center distributing groceries and prepared meals to families in need. Open Tuesday-Saturday, registration required for regular assistance.',
                'address': 'USJ 1, 47620 Subang Jaya, Selangor',
                'phone': '+60-3-8024-5577',
                'latitude': 3.0435,
                'longitude': 101.5877,
                'capacity_current': 180,
                'capacity_max': 200,
                'status': 'limited',
                'is_emergency': False,
            },

            # Shelter & Housing
            {
                'name': 'Rumah Perlindungan Wanita Selangor',
                'category': categories['shelter'],
                'description': 'Safe house for women and children escaping domestic violence. 24/7 hotline available. Provides temporary accommodation, counseling, and legal assistance.',
                'address': 'Seksyen 2, 40000 Shah Alam, Selangor',
                'phone': '+60-3-5544-7788',
                'latitude': 3.0833,
                'longitude': 101.5333,
                'capacity_current': 25,
                'capacity_max': 35,
                'status': 'open',
                'is_emergency': True,
            },
            {
                'name': 'Pusat Transit Gelandangan KL',
                'category': categories['shelter'],
                'description': 'Temporary shelter for homeless individuals providing basic accommodation, meals, and support services to help people get back on their feet.',
                'address': 'Chow Kit, 50300 Kuala Lumpur, Wilayah Persekutuan',
                'phone': '+60-3-2693-9922',
                'latitude': 3.1667,
                'longitude': 101.6833,
                'capacity_current': 40,
                'capacity_max': 50,
                'status': 'open',
                'is_emergency': True,
            },
            {
                'name': 'Rumah Selamat Anak Jalanan',
                'category': categories['shelter'],
                'description': 'Shelter and rehabilitation center for street children providing education, skills training, and family reunification services.',
                'address': 'Seksyen 7, 68000 Ampang, Selangor',
                'phone': '+60-3-4270-1133',
                'latitude': 3.1500,
                'longitude': 101.7667,
                'capacity_current': 30,
                'capacity_max': 45,
                'status': 'open',
                'is_emergency': False,
            },

            # Emergency Services
            {
                'name': 'Balai Bomba Shah Alam',
                'category': categories['emergency'],
                'description': '24/7 fire and rescue services covering Shah Alam and surrounding areas. Emergency response for fires, accidents, and natural disasters.',
                'address': 'Seksyen 4, 40000 Shah Alam, Selangor',
                'phone': '999',
                'latitude': 3.0833,
                'longitude': 101.5167,
                'capacity_current': 0,
                'capacity_max': 0,
                'status': 'open',
                'is_emergency': True,
            },
            {
                'name': 'Ibu Pejabat Polis Kontinjen Selangor',
                'category': categories['emergency'],
                'description': 'Main police headquarters for Selangor state providing law enforcement, crime investigation, and emergency response services.',
                'address': 'Jalan Stadium, Seksyen 13, 40100 Shah Alam, Selangor',
                'phone': '999',
                'latitude': 3.0667,
                'longitude': 101.5000,
                'capacity_current': 0,
                'capacity_max': 0,
                'status': 'open',
                'is_emergency': True,
            },
            {
                'name': 'Pusat Bantuan Bencana Alam',
                'category': categories['emergency'],
                'description': 'Disaster relief center coordinating emergency response during floods, earthquakes, and other natural disasters. Provides evacuation assistance and supplies.',
                'address': 'Bangunan SUK, 40503 Shah Alam, Selangor',
                'phone': '+60-3-5544-1000',
                'latitude': 3.0667,
                'longitude': 101.5167,
                'capacity_current': 500,
                'capacity_max': 1000,
                'status': 'open',
                'is_emergency': True,
            },

            # Education Services
            {
                'name': 'Pusat Pembelajaran Komuniti Selangor',
                'category': categories['education'],
                'description': 'Adult education center offering literacy programs, skills training, and vocational courses. Free classes for disadvantaged adults seeking to improve their qualifications.',
                'address': 'Seksyen 9, 40000 Shah Alam, Selangor',
                'phone': '+60-3-5511-4455',
                'latitude': 3.0667,
                'longitude': 101.5333,
                'capacity_current': 120,
                'capacity_max': 150,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Perpustakaan Awam Petaling Jaya',
                'category': categories['education'],
                'description': 'Public library with extensive collection of books, digital resources, and study spaces. Free computer and internet access, reading programs for children.',
                'address': 'Jalan Amcorp, 46050 Petaling Jaya, Selangor',
                'phone': '+60-3-7958-3123',
                'latitude': 3.1167,
                'longitude': 101.6500,
                'capacity_current': 200,
                'capacity_max': 300,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Program Tuisyen Percuma Selayang',
                'category': categories['education'],
                'description': 'Free tutoring program for primary and secondary students from low-income families. Evening classes available Monday-Friday with qualified volunteer teachers.',
                'address': 'Taman Selayang Utama, 68100 Batu Caves, Selangor',
                'phone': '+60-3-6136-2244',
                'latitude': 3.2333,
                'longitude': 101.6833,
                'capacity_current': 80,
                'capacity_max': 100,
                'status': 'open',
                'is_emergency': False,
            },

            # Social Services
            {
                'name': 'Jabatan Kebajikan Masyarakat Selangor',
                'category': categories['social'],
                'description': 'State social welfare department providing financial assistance, counseling services, and support programs for families, elderly, and disabled persons.',
                'address': 'Wisma Darul Ehsan, 40503 Shah Alam, Selangor',
                'phone': '+60-3-5544-2000',
                'latitude': 3.0667,
                'longitude': 101.5000,
                'capacity_current': 0,
                'capacity_max': 0,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Pusat Jagaan Warga Emas Bangi',
                'category': categories['social'],
                'description': 'Elderly care center providing day care services, healthcare, recreational activities, and social support for senior citizens in the Bangi area.',
                'address': 'Seksyen 4, 43650 Bandar Baru Bangi, Selangor',
                'phone': '+60-3-8925-4466',
                'latitude': 2.9167,
                'longitude': 101.7833,
                'capacity_current': 60,
                'capacity_max': 80,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Rumah Perlindungan Anak Yatim',
                'category': categories['social'],
                'description': 'Orphanage providing residential care, education, and emotional support for orphaned and abandoned children. Adoption and fostering services available.',
                'address': 'Taman Tun Dr Ismail, 60000 Kuala Lumpur, Wilayah Persekutuan',
                'phone': '+60-3-7728-3344',
                'latitude': 3.1333,
                'longitude': 101.6333,
                'capacity_current': 45,
                'capacity_max': 60,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Kaunseling Keluarga Selangor',
                'category': categories['social'],
                'description': 'Family counseling center offering marriage counseling, family therapy, and support for domestic issues. Professional counselors available by appointment.',
                'address': 'Seksyen 14, 40000 Shah Alam, Selangor',
                'phone': '+60-3-5519-7799',
                'latitude': 3.0667,
                'longitude': 101.5167,
                'capacity_current': 0,
                'capacity_max': 0,
                'status': 'open',
                'is_emergency': False,
            },
            {
                'name': 'Pusat Sokongan OKU Selangor',
                'category': categories['social'],
                'description': 'Support center for persons with disabilities providing skills training, job placement assistance, and advocacy services. Accessible facilities and specialized programs.',
                'address': 'Seksyen 7, 40000 Shah Alam, Selangor',
                'phone': '+60-3-5511-6677',
                'latitude': 3.0738,
                'longitude': 101.5183,
                'capacity_current': 100,
                'capacity_max': 120,
                'status': 'open',
                'is_emergency': False,
            },
        ]

        # Create services
        for service_data in services_data:
            service = Service.objects.create(**service_data)
            self.stdout.write(
                self.style.SUCCESS(f'Created service: {service.name}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {len(services_data)} sample services!')
        ) 