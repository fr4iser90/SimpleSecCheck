# SecuLite v2 - Architectural Decisions

This document records the key architectural decisions made during the planning phase of SecuLite v2.

## Table of Contents

1.  [Backend Framework](#1-backend-framework)
2.  [Database System](#2-database-system)
3.  [Background Task Queue](#3-background-task-queue)
4.  [Frontend Approach](#4-frontend-approach)
    *   *(Further decisions will be added as we progress)*

---

## 1. Backend Framework

*   **Status:** Decided

### 1.1. Decision Statement

SecuLite v2 will use **Django** as its backend framework.

### 1.2. Context & Problem Statement

SecuLite v2 requires a robust backend to manage multiple scan targets, orchestrate scan execution via a task queue, handle user authentication and authorization, persist data to a database, and serve a comprehensive API for a rich web frontend. The current Flask-based simple web server (`web/app.py`) is insufficient for this complexity and lacks proper structure for a scalable and maintainable platform.

We need to select a Python backend framework that:
-   Provides strong support for building RESTful APIs.
-   Integrates well with ORMs for database interaction.
-   Supports or can be easily integrated with authentication mechanisms.
-   Is scalable and maintainable for a growing feature set.
-   Has a good ecosystem and community support.

### 1.3. Considered Options

The following Python backend frameworks were considered:

*   **Option A: Enhanced Flask**
    *   **Description:** Continue using Flask but adopt a more structured approach using Blueprints for modularity, SQLAlchemy as an ORM, Flask-Login/Flask-Security for authentication, and integrate with Celery for task management. This builds upon the existing minimal Flask usage.
*   **Option B: Django**
    *   **Description:** Adopt Django, a high-level Python web framework that encourages rapid development and clean, pragmatic design. It comes with many built-in features, including an ORM, admin panel, and authentication system.
*   **Option C: FastAPI**
    *   **Description:** Utilize FastAPI, a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints. It's known for its speed, automatic data validation, and interactive API documentation (Swagger UI/ReDoc).

### 1.4. Pros & Cons of Options

**Option A: Enhanced Flask**
*   **Pros:**
    *   **Flexibility & Simplicity:** Flask is minimalist and unopinionated, giving full control over component choices and project structure.
    *   **Lower Initial Learning Curve (for Flask basics):** If already familiar with basic Flask, the initial step isn't as large.
    *   **Large Ecosystem of Extensions:** Many mature extensions are available (SQLAlchemy for ORM, Flask-Login/Flask-Security for auth, Flask-RESTful/Flask-API for APIs).
    *   **Good for Smaller to Medium Applications:** Can be very effective if well-structured.
*   **Cons:**
    *   **"Framework by Assembly":** Requires more boilerplate and manual integration of components (ORM, auth, admin interface, task queue integration). This can slow down initial development of core platform features for a large project.
    *   **Scalability & Maintainability Challenges:** As the application grows, maintaining a cohesive structure requires more discipline without the strong conventions of a larger framework.
    *   **Admin Interface:** No built-in admin panel; would require Flask-Admin or custom development.
    *   **Security:** Responsibility for implementing security best practices for auth, sessions, CSRF, etc., falls more on the developer and the chosen extensions.

**Option B: Django**
*   **Pros:**
    *   **"Batteries Included":** Comes with a powerful ORM, an automatic admin interface, a robust authentication system, and a clear project structure out-of-the-box. This significantly speeds up development of core platform features.
    *   **Rapid Development:** Many common web application features are built-in or easily added.
    *   **Scalability:** Proven to scale for very large applications.
    *   **Security:** Includes built-in protections against common web vulnerabilities.
    *   **Excellent Documentation & Large Community:** Easy to find help and resources.
    *   **Mature Ecosystem:** Django REST framework (DRF) is a powerful toolkit for building web APIs.
*   **Cons:**
    *   **Monolithic & Opinionated:** Can feel "heavy" or restrictive if one wants to deviate significantly from "the Django way."
    *   **Steeper Learning Curve (initially):** More concepts to learn initially compared to Flask (e.g., Django's ORM, settings, project/app structure).

**Option C: FastAPI**
*   **Pros:**
    *   **High Performance:** One of the fastest Python frameworks available.
    *   **Modern Python Features:** Leverages Python type hints for data validation, serialization, and automatic API documentation.
    *   **Easy to Learn (for API development):** Intuitive syntax if familiar with Python type hints.
    *   **Automatic API Docs:** Excellent for developing and consuming the API.
    *   **Good for API-First Development:** Designed primarily for building APIs.
*   **Cons:**
    *   **Not a Full-Stack Framework:** Primarily focused on the API layer. Requires manual integration of ORM, authentication, admin interface, etc., similar to Flask for full platform needs.
    *   **Younger Ecosystem (than Django/Flask):** The ecosystem for full-stack components (like a comprehensive admin panel) is less mature.
    *   **Database Interaction:** Requires integrating an ORM; not as "built-in" as Django's ORM.

### 1.5. Final Decision & Rationale

**Decision: Django**

**Rationale:** For SecuLite v2, envisioned as a large, scalable platform with comprehensive features (database, user management, multi-target scanning, background tasks, rich UI), Django offers the most advantages:
-   Its **"batteries-included"** nature provides many essential components (ORM, auth, admin panel) out-of-the-box, accelerating the development of core platform functionalities.
-   Django is **proven to scale** for large applications and provides a **clear, maintainable structure**, which is crucial for a project of this intended scope and complexity.
-   The built-in **security features** and the extensive **ecosystem (including Django REST Framework)** provide a solid foundation for building a secure and robust API-driven platform.
-   While there's an initial learning curve, the long-term benefits of its comprehensive feature set and established best practices outweigh the initial setup time for a project aiming to be a feature-rich monitoring tool.

---

## 2. Database System

*   **Status:** Decided

### 2.1. Decision Statement

SecuLite v2 will use **PostgreSQL** as its primary database system.

### 2.2. Context & Problem Statement

SecuLite v2 requires a persistent and reliable data store for various platform entities, including:
-   User accounts, profiles, and authentication tokens.
-   Definitions and configurations of multiple scan targets (URLs, code paths, image names).
-   Historical scan results, including individual findings, their severity, status (new, acknowledged, resolved), and timestamps.
-   Configuration settings for the platform and individual scans.
-   Logs related to LLM interactions and generated analyses.
-   Data for trend analysis and reporting over time.

A relational database management system (RDBMS) is well-suited for this structured data and the relationships between these entities. The chosen Django backend has excellent support for various RDBMS through its ORM.

### 2.3. Considered Options

*   **Option A: PostgreSQL**
    *   **Description:** A powerful, open-source object-relational database system with a strong reputation for reliability, feature robustness, and data integrity.
*   **Option B: MySQL/MariaDB**
    *   **Description:** Widely used open-source relational database systems. MariaDB is a community-developed fork of MySQL.
*   **Option C: SQLite**
    *   **Description:** A C-library that provides a lightweight, disk-based database. It doesn't require a separate server process and is very easy to set up.

### 2.4. Pros & Cons of Options

**Option A: PostgreSQL**
*   **Pros:**
    *   **Excellent Django Integration:** Often considered the preferred database for Django projects, with mature and well-tested adapter (`psycopg2`).
    *   **Advanced Features:** Supports complex queries, full-text search, JSONB data types (useful for storing flexible metadata or scan outputs), and a wide array of extensions.
    *   **Scalability & Reliability:** Known for its robustness and ability to handle large datasets and high concurrency.
    *   **Data Integrity:** Strong adherence to SQL standards and robust transactional capabilities.
    *   **Open Source & Strong Community:** Actively developed and well-supported.
*   **Cons:**
    *   **Slightly More Complex Setup/Management (than SQLite):** Requires a separate server process and potentially more configuration for optimal performance.

**Option B: MySQL/MariaDB**
*   **Pros:**
    *   **Good Django Support:** Also well-supported by Django's ORM.
    *   **Widely Used & Known:** Large user base and readily available hosting/support.
    *   **Performance:** Can be very performant, especially for read-heavy workloads.
*   **Cons:**
    *   **Feature Set (Historically):** While improving, historically PostgreSQL has been seen as having a richer feature set for complex applications (e.g., advanced indexing, certain data types).
    *   **Licensing (MySQL):** Oracle's ownership of MySQL sometimes raises concerns, leading many to prefer MariaDB.

**Option C: SQLite**
*   **Pros:**
    *   **Simplicity:** Extremely easy to set up and use; it's just a file. Ideal for development, testing, and small, single-user applications.
    *   **Built into Python:** No external dependencies needed for basic use.
*   **Cons:**
    *   **Concurrency Limitations:** Not well-suited for applications with multiple concurrent writers, which SecuLite v2 will have (web requests, background scan workers updating the database).
    *   **Scalability:** Does not scale well for large datasets or high traffic.
    *   **Limited Feature Set:** Lacks many advanced features of server-based RDBMS like PostgreSQL or MySQL.
    *   **Not Recommended for Production (for this type of application):** While fine for development, it's generally not recommended as the primary production database for a web platform like SecuLite v2.

### 2.5. Final Decision & Rationale

**Decision: PostgreSQL**

**Rationale:** PostgreSQL is selected as the database system for SecuLite v2 due to several key advantages aligned with the project's goals:
-   **Optimal Django Synergy:** Its seamless integration with Django's ORM and widespread use in the Django community make it a natural fit.
-   **Robustness and Scalability:** PostgreSQL is well-regarded for its ability to handle complex data, large volumes, and concurrent access, which is essential for a growing monitoring platform.
-   **Advanced Feature Set:** Features like JSONB support, powerful indexing, and transactional integrity are highly beneficial for storing diverse scan data and ensuring data consistency.
-   **Open Source and Community:** Being open-source with a strong community ensures long-term viability and support.

While SQLite is excellent for development and testing due to its simplicity, PostgreSQL provides the necessary power and scalability for the production environment of SecuLite v2. MySQL/MariaDB are viable alternatives but PostgreSQL's feature set and strong Django pairing give it an edge for this project.

---

## 3. Background Task Queue

*   **Status:** Decided

### 3.1. Decision Statement

SecuLite v2 will use **Celery** as its distributed task queue framework, with **Redis** serving as the message broker and potentially as the results backend.

### 3.2. Context & Problem Statement

Security scans (especially DAST like ZAP, or SAST on large codebases) can be time-consuming operations. Running these synchronously within a web request would lead to timeouts and a poor user experience. SecuLite v2 needs a system to:
-   Execute scan tasks asynchronously in the background.
-   Manage a queue of pending scan jobs.
-   Support scheduled/periodic scans.
-   Provide mechanisms for task monitoring, retries, and potentially prioritization.
-   Integrate smoothly with the Django backend.

### 3.3. Considered Options

*   **Option A: Celery with Redis**
    *   **Description:** Celery is a mature, feature-rich distributed task queue system for Python. Redis is a popular in-memory data store often used as a fast and efficient message broker and results backend for Celery.
*   **Option B: Celery with RabbitMQ**
    *   **Description:** Similar to Option A, but uses RabbitMQ as the message broker. RabbitMQ is a more traditional, robust message broker offering features like message persistence, complex routing, and better guarantees for message delivery in some scenarios.
*   **Option C: Django-Q / RQ (Python Redis Queue)**
    *   **Description:** These are simpler task queue libraries built on top of Redis. They are generally easier to set up than Celery but offer fewer advanced features.

### 3.4. Pros & Cons of Options

**Option A: Celery with Redis**
*   **Pros:**
    *   **Excellent Django Integration:** Celery is the de-facto standard for background tasks in Django projects.
    *   **Very Feature-Rich:** Supports scheduled tasks (Celery Beat), retries, complex workflows, rate limiting, and good monitoring (e.g., Flower).
    *   **Highly Scalable:** Designed for distributed systems.
    *   **Redis Performance & Simplicity:** Redis is fast, lightweight, and relatively easy to manage as a broker.
    *   **Large Community & Documentation:** Abundant resources and support.
*   **Cons:**
    *   **Celery Complexity:** Can be complex to configure for advanced scenarios.
    *   **Redis Message Persistence:** While Redis can persist, it's primarily in-memory; a crash *could* lead to message loss if not carefully configured (AOF/RDB), though Celery's acknowledgments help.

**Option B: Celery with RabbitMQ**
*   **Pros:**
    *   **All Celery Pros (as above).**
    *   **RabbitMQ Robustness:** Dedicated message broker with strong message persistence, delivery guarantees, and advanced routing.
    *   **Enterprise-Ready:** Often favored where message durability is paramount.
*   **Cons:**
    *   **Increased Complexity (vs. Redis):** RabbitMQ is more complex to set up, manage, and monitor.
    *   **Higher Resource Usage (vs. Redis).**

**Option C: Django-Q / RQ (Python Redis Queue)**
*   **Pros:**
    *   **Simplicity:** Significantly easier to set up and configure than Celery.
    *   **Lightweight:** Less overhead.
    *   **Good for Simpler Use Cases:** Effective for basic background tasks and simple scheduling.
    *   **Direct Django Integration (Django-Q):** Django-Q offers a convenient admin interface.
*   **Cons:**
    *   **Fewer Advanced Features (than Celery):** Lacks some of Celery's advanced workflow, routing, and extensive monitoring capabilities.
    *   **Scalability:** While capable, Celery is more proven for extremely high-volume, distributed loads.
    *   **Smaller Ecosystem (than Celery).**

### 3.5. Final Decision & Rationale

**Decision: Celery with Redis**

**Rationale:** For SecuLite v2, Celery with Redis provides the best balance of power, features, scalability, and operational manageability:
-   **Celery's Rich Feature Set:** Essential for handling diverse scan tasks, scheduling, retries, and potential future complex workflows (e.g., multi-step analysis involving LLMs).
-   **Redis's Performance and Simplicity:** Redis serves as a fast and efficient message broker, is well-supported, and is simpler to manage within a Dockerized environment compared to RabbitMQ. This is a good starting point for a self-hosted platform.
-   **Strong Django Integration:** This combination is a standard and well-documented stack within the Django ecosystem, ensuring good community support and available resources.
-   **Sufficient Reliability:** For scan tasks, the combination of Celery's task acknowledgment mechanisms and the ease of re-queueing scans (if an extreme broker failure occurred) provides an acceptable level of reliability. The primary concern is not losing scan *jobs*; the critical scan *data* will reside in PostgreSQL.
-   **Scalability with Manageable Overhead:** Celery can scale out with more workers as needed, and Redis is less resource-intensive than RabbitMQ, keeping operational overhead reasonable.

This choice aligns with the goal of building a robust and scalable platform without introducing unnecessary complexity too early in the development lifecycle.

---

## 4. Frontend Approach

*   **Status:** Decided

### 4.1. Context & Problem Statement

SecuLite v2 aims to be a comprehensive security monitoring platform. The frontend will be the primary way users interact with the system to:
-   Configure scan targets (web applications, code repositories, container images).
-   View scan results, dashboards, and historical trends.
-   Manage findings (acknowledge, mark as false positive, track resolution).
-   Manage user accounts and platform settings.
-   Receive real-time (or near real-time) updates on scan progress and new findings.

The frontend needs to be:
-   **User-Friendly & Intuitive:** Easy to navigate and understand, even for users who may not be security experts.
-   **Responsive & Performant:** Provide a smooth experience without noticeable lag, especially when displaying large amounts of data (e.g., many findings).
-   **Interactive:** Allow users to easily filter, sort, and interact with data.
-   **Maintainable & Scalable:** The chosen approach should allow for future feature additions and UI enhancements without excessive complexity.
-   **Secure:** Follow best practices for frontend security.

Given that we have chosen Django for the backend (which can serve APIs and/or HTML templates), we need to decide on the best frontend architecture to meet these requirements.

### 4.2. Considered Options

*   **Option A: Django Templates with Sprinkles of JavaScript (e.g., HTMX, Alpine.js, or vanilla JS)**
    *   **Description:** Leverage Django's templating engine to render most of the UI on the server-side. Use minimal JavaScript for dynamic interactions, potentially with lightweight libraries like HTMX (for AJAX-powered partial page updates without writing much JS) or Alpine.js (for reactive components).
*   **Option B: Single Page Application (SPA) with a Modern JavaScript Framework (e.g., React, Vue, or Svelte)**
    *   **Description:** Build a rich client-side application using a JavaScript framework. The frontend would be a separate codebase (or a distinct part of the monorepo) that communicates with the Django backend exclusively via RESTful APIs (which Django REST Framework is well-suited to provide).
*   **Option C: Hybrid Approach / Next-gen Multi-Page App (MPA) (e.g., Next.js, Nuxt.js, SvelteKit with Django API)**
    *   **Description:** Utilize a full-stack JavaScript framework that offers features like server-side rendering (SSR), static site generation (SSG), client-side navigation, and an optimized developer experience. This would still consume APIs from the Django backend but might involve a Node.js layer for the frontend server aspects.

### 4.3. Pros & Cons of Options

**Option A: Django Templates with Sprinkles of JavaScript**
*   **Pros:**
    *   **Simplicity & Rapid Initial Development:** Leverages existing Django development skills and Django's mature templating system. Less context switching between frontend and backend languages/frameworks for the core team.
    *   **SEO-Friendly (by default):** Server-rendered HTML is inherently easy for search engines to crawl and index.
    *   **Lower Complexity for Many Common UI Patterns:** Ideal for applications that are primarily form-based or content-driven with moderate interactivity (e.g., dashboards, settings pages, lists with sorting/filtering).
    *   **Reduced JavaScript "Fatigue":** Avoids the need to learn and manage a large JavaScript framework, build tools, and complex state management if not strictly necessary. Libraries like HTMX or Alpine.js can provide significant dynamic enhancements with minimal JS.
    *   **Unified Codebase & Deployment (mostly):** Frontend templates are part of the Django project, simplifying the build and deployment process compared to a separate SPA.
*   **Cons:**
    *   **Limited Interactivity for Complex UIs:** Can become cumbersome for highly dynamic, real-time interfaces or UIs that require extensive client-side state management (e.g., a complex findings triage board with drag-and-drop and live updates).
    *   **Full Page Reloads (traditionally):** Without tools like HTMX, user interactions often lead to full page reloads, which can feel less smooth. HTMX significantly mitigates this by enabling partial page updates.
    *   **Client-Side State Management:** Managing complex client-side state can become ad-hoc and harder to maintain as features grow, relying on scattered JavaScript or simpler stores.
    *   **API Design as an Afterthought:** May not enforce a clean, API-first design from the outset, which could be a drawback if a dedicated SPA or mobile client is envisioned later.
    *   **Reusability for Native Mobile Apps:** The UI logic embedded in Django templates is not directly reusable if a native mobile application is ever planned.

**Option B: Single Page Application (SPA) with a Modern JavaScript Framework (React, Vue, Svelte)**
*   **Pros:**
    *   **Rich & Highly Interactive UIs:** Excellent for building complex, desktop-like web applications with sophisticated client-side state, real-time updates, and smooth transitions.
    *   **Improved User Experience (for dynamic UIs):** No full page reloads after the initial load, leading to a faster, more fluid feel for users navigating within the application.
    *   **Clear Separation of Concerns:** Enforces a decoupled architecture where the frontend (SPA) and backend (Django API) are distinct. This promotes a clean API design (via Django REST Framework).
    *   **Reusable API:** The API built to serve the SPA can be readily consumed by other clients, such as native mobile apps, third-party integrations, or command-line tools.
    *   **Large Talent Pool & Mature Ecosystems:** Frameworks like React, Vue, and Svelte have vast communities, extensive libraries, UI component kits, and a large pool of developers.
    *   **Potentially Better Perceived Performance (after initial load):** Once the SPA is loaded, subsequent navigation and interactions can be very fast.
*   **Cons:**
    *   **Increased Complexity:** Requires managing at least two distinct codebases/projects (frontend SPA and backend API), each with its own build process, dependencies, and development environment.
    *   **Higher Initial Development Effort & Learning Curve:** Setting up the SPA, build tools (Webpack/Vite), routing, global state management (Redux, Vuex, Zustand), and robust API communication takes significant upfront effort and specialized JavaScript framework knowledge.
    *   **SEO Challenges (traditionally):** SPAs often require server-side rendering (SSR) or pre-rendering solutions to be properly indexed by search engines, adding another layer of complexity. (Less critical for SecuLite v2 if it's an internal/authenticated tool).
    *   **JavaScript Expertise Required:** Demands a team with strong JavaScript skills and proficiency in the chosen SPA framework.
    *   **Larger Initial Load Time & Bundle Size:** The initial download of the JavaScript bundle for the SPA can be substantial, potentially leading to a slower first-page experience if not optimized (e.g., via code-splitting).
    *   **Authentication & Security:** Requires careful handling of token-based authentication (e.g., JWTs, OAuth) and ensuring security best practices are followed on both client and server sides for API interactions.

**Option C: Hybrid Approach / Next-gen Multi-Page App (MPA) (e.g., Next.js, Nuxt.js, SvelteKit with Django API)**
*   **Pros:**
    *   **Potential "Best of Both Worlds":** Can offer SPA-like rich interactivity and client-side navigation while providing better SEO and faster initial page loads through server-side rendering (SSR) or static site generation (SSG) capabilities.
    *   **Optimized Developer Experience:** These full-stack JavaScript frameworks (Next.js for React, Nuxt.js for Vue, SvelteKit for Svelte) often come with excellent tooling, opinionated project structures, file-system based routing, and optimized data-fetching patterns.
    *   **Performance Benefits:** Can be highly performant due to features like SSR/SSG, image optimization, and smart bundling.
    *   **Still Consumes Django API:** Allows Django to focus on its strengths as a robust API backend, while the JS framework handles the view layer and user experience.
*   **Cons:**
    *   **Highest Complexity:** Introduces another significant layer – the Node.js server environment for the frontend framework – in addition to the Django backend. This means managing two server environments and potentially two different languages/ecosystems at a deep level.
    *   **Deployment & Infrastructure Complexity:** Deploying and maintaining both a Django backend and a Node.js-based frontend application can be more involved and require more sophisticated infrastructure.
    *   **Potential for "Overkill":** Might be more than needed if the UI requirements are not extremely complex or do not critically depend on cutting-edge frontend features like SSR for public-facing SEO (which might be less critical for an internal-facing security tool).
    *   **Broader Team Skillset Required:** Requires expertise in both Django (for the API) and the chosen full-stack JavaScript framework and its underlying ecosystem (e.g., React/Next.js or Vue/Nuxt.js).
    *   **Build Times & Resource Usage:** These frameworks can sometimes have longer build times and higher resource usage during development and deployment compared to simpler approaches.

### 4.4. Decision Statement

SecuLite v2 will use a **Single Page Application (SPA)** architecture for its frontend, built with the **Vue.js** framework.

### 4.5. Final Decision & Rationale

**Decision: Single Page Application (SPA) with Vue.js**

**Rationale:** The Single Page Application (SPA) approach (Option B) is selected for SecuLite v2 due to its superior ability to deliver a rich, interactive, and responsive user experience. This is crucial for a platform designed to manage complex security scan data, display detailed dashboards, and allow for interactive management of findings.

Key factors influencing this decision include:
-   **Rich User Experience:** SPAs excel at creating dynamic, app-like interfaces without full page reloads, leading to a smoother and more engaging experience for users interacting with scan results, configurations, and analytics.
-   **API-Driven Architecture:** This choice naturally complements our Django backend, which will serve a comprehensive REST API via Django REST Framework. This clear separation of concerns between the frontend and backend enhances modularity, maintainability, and allows both components to evolve more independently.
-   **Scalability for Complex Features:** As SecuLite v2 grows, an SPA provides a more robust foundation for adding complex client-side features and managing UI state effectively.
-   **Reusable Backend API:** The API developed for the Vue.js SPA can be easily consumed by other clients in the future, such as CLI tools or potential third-party integrations.

**Vue.js** is chosen as the specific JavaScript framework because:
-   **Balance of Power and Simplicity:** Vue.js is renowned for its gentle learning curve, clear syntax, and excellent documentation, making it approachable while still being powerful enough for complex applications.
-   **Strong Ecosystem & Tooling:** It has a mature ecosystem, including Vue Router for client-side routing, Pinia/Vuex for state management, and a wide array of UI component libraries (like Vuetify, Quasar, or PrimeVue) that can accelerate the development of a polished and professional-looking interface.
-   **Performance:** Vue.js is known for its good performance characteristics.
-   **Community Support:** It has a large and active global community.

While this approach involves managing a separate frontend codebase and requires JavaScript expertise, the long-term benefits for user experience, architectural clarity, and future scalability for SecuLite v2 outweigh the initial setup overhead. SEO is a lesser concern for this type of authenticated platform, mitigating one of the common drawbacks of SPAs.

--- 