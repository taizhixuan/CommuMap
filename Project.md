## Abstract&#x20;

The Community Resource Mapping & Public Services Locator (CommuMap) is a web-based platform that empowers residents to discover, evaluate, and access essential community resources—including clinics, shelters, libraries, food banks, emergency centers, and learning hubs—through a single interactive map.

**Key capabilities include:**

* Real-time, geo-accurate listings that display operating hours, contact details, capacity indicators, and urgent alerts (e.g., temporary closures or crowding).
* A “Help Me Now” emergency filter that instantly shows only verified, open, emergency-eligible services within the user’s immediate vicinity.
* **Role-based collaboration:**

  * *Service Managers* (e.g., clinic directors) maintain their own listings and push live capacity or closure updates.
  * *Community Moderators* verify new services and moderate user feedback.
  * *Admins* oversee security, user roles, and system-wide announcements.
* Crowdsourced feedback and comments with automated and human moderation to sustain data quality and community trust.
* Mobile-responsive design to serve users on any device, including those with limited digital resources.

By aggregating fragmented information into a single, user-friendly interface, CommuMap directly advances UN Sustainable Development Goal 10 (Reduced Inequalities) and Goal 11 (Sustainable Cities & Communities). The platform’s methodological approach—combining GIS technology, real-time data pipelines, and participatory moderation—ensures accuracy, inclusivity, and resilience. Ultimately, CommuMap reduces the time and effort required for individuals, especially vulnerable populations, to locate critical services, while providing local authorities and NGOs with actionable insights to address service gaps and plan resource allocation more effectively.

---

## Introduction&#x20;

### 1.1 Abstract

CommuMap is a web-based platform that unifies—and keeps current—critical community-service information (clinics, shelters, food banks, libraries, emergency hubs, learning centers). Through an intuitive, mobile-first map, residents can:

* Locate services in seconds with category chips, distance sliders, and a one-tap “Help Me Now” emergency filter.
* Trust the data—operating hours, live capacity indicators, and closure alerts are updated directly by verified Service Managers and double-checked by Community Moderators.
* Improve the map by posting ratings, comments, and correction suggestions, all backed by a transparent moderation queue.

Real-time data pipelines, role-based governance, and participatory feedback loops ensure both accuracy and inclusivity. By lowering the “information barrier” that disproportionately affects vulnerable populations, CommuMap advances SDG 10 (Reduced Inequalities) and SDG 11 (Sustainable Cities & Communities), helping municipalities build more resilient, equitable service networks.

### 1.2 Problem Statement

Residents often confront a scattered landscape of outdated flyers, static PDF directories, and poorly maintained websites when seeking basic social services. Consequences include:

* **Fragmentation** – information is spread across multiple agencies with no single source of truth.
* **Staleness** – manual updates mean hours or capacity data become obsolete within days.
* **Poor usability** – many portals are not mobile-friendly and lack accessibility features.
* **Limited feedback loops** – citizens cannot easily flag inaccuracies; providers struggle to broadcast urgent changes.
* **Equity gap** – people with low digital literacy, disabilities, or limited data plans face the steepest hurdles.

These shortcomings lead to missed medical appointments, wasted journeys to full shelters, and slower emergency response—all of which deepen social inequality. A centralised, real-time, and participatory mapping solution is urgently needed.

---

## Project Objectives&#x20;

* To design and implement a centralized web platform that enables users to search for, view, and filter essential community services via an interactive map interface.
* To support real-time service updates and changes made by authorized service managers, ensuring consistent and reliable information.
* To empower users and service providers to collaborate through feedback and updates, enhancing transparency, inclusivity, and trust in community support systems.
* To contribute to global efforts under SDG 10 by reducing disparities in service access and to SDG 11 by improving the infrastructure and accessibility of urban and rural communities.

---

## Project and System Scope&#x20;

### Project Scope

The Community Resource Mapping & Public Services Locator System project aims to design and develop a web-based platform that enables the public to access and locate essential community resources efficiently. The platform will support an interactive map interface, real-time updates, and feedback features to ensure the accuracy and usefulness of information. The project will focus on creating a user-friendly, scalable, and maintainable system that benefits both the public and organizations managing public services.

The system will be developed using modern web technologies and follow best practices in user experience, data handling, and system performance. The development process will include planning, analysis, system design, implementation, and testing phases. Key project deliverables include a functional prototype, documentation, and user feedback mechanisms.

### System Scope

**In-Scope Functionalities**

* Interactive Map – real-time rendering of clinics, shelters, libraries, food banks, etc.
* Advanced Search & Filter – by category, distance, Status.
* Live Status Feeds – operating hours, Real-Time Capacity Indicators (pins pulse red ≥ 90 % full).
* Localized Emergency Button – one-tap “Help Me Now” view of verified, open emergency resources within default 5 km radius.
* User Feedback Loop – ratings, comments, and “suggest edit” form with moderator workflow.

**Role-Based Dashboards**

* **Service Manager:** add/edit listings, push closure alerts, update capacity, generate reports.
* **Community Moderator:** approve listings, moderate content, publish outreach posts.
* **Admin:** manage users & roles, tag emergency services, broadcast system-wide banners, perform platform maintenance.

Responsive UI – single code-base optimised for desktop, tablet, and low-end mobile browsers.

---

## Business Rule&#x20;

1. **General Service Management**

   * All service listings must include basic information:

     * Name of the Service
     * Physical Address
     * Geographic Coordinates (latitude and longitude)
     * Type of Service (Clinic, Shelter, Library, Food Bank, Emergency Center, etc.)
     * Contact Information (phone, email)
     * Regular Operating Hours
     * Emergency Service Eligibility Status (Yes/No)
   * Service Managers (clinic managers, shelter managers, etc.) create and maintain their service listings.
   * All newly created or significantly updated listings (change of location, service type, or eligibility status) require secondary verification and approval by Admin or Community Moderator within 24 hours before public visibility.
   * Service Managers must regularly update their service’s real-time capacity indicators:

     * At least once every 12 hours during standard operation.
     * Immediately upon significant capacity changes.

2. **User Access & Permissions**

   * **Users:** Search services, bookmark favorites, and submit feedback or comments.
   * **Service Managers:** Verified managers of specific services (e.g., clinic or shelter managers) who can manage service details, update real-time status, and monitor capacity.
   * **Community Moderators:** review and approve submitted listings, moderate user comments and feedback.
   * **Admins:** System-wide managers responsible for managing all user accounts, verifying roles, approve emergency tags, oversee content moderation, and perform system maintenance.

3. **Service Manager Verification**

   * Service Managers must register by submitting their official details (full name, official email, contact number, and service name).
   * Admin reviews and verifies identity through official communication or provided documents before granting full access.
   * Admin periodically reviews updates by Service Managers to maintain accuracy.

4. **Verification of Community Moderators**

   * Community Moderators apply by submitting their details (full name, email, relevant community or moderation experience).
   * Admin reviews applications and confirms identity and experience.
   * Upon approval, moderators are given access to moderation tools.
   * Admin regularly reviews moderator actions for compliance and quality assurance.

5. **Admin Account Management**

   * Admin accounts are created and managed only by existing Admins or authorized personnel.

6. **Data Quality & Moderation**

   * All service listings require verification by Admin or Moderators before becoming publicly visible.
   * User feedback and comments must undergo moderation to ensure relevance and appropriateness.

7. **Search & Discovery**

   * Users can filter searches by category, distance, ans status.
   * The "Help Me Now" emergency button displays only nearby emergency-tagged services that are currently open.
   * Services nearing full capacity are visually indicated (e.g., red markers) on the interactive map.

8. **Security & Privacy**

   * Admin, Moderator, and Service Manager accounts require secure authentication.
   * User consent for data collection is clearly obtained during registration.
