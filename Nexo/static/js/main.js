document.addEventListener("DOMContentLoaded", function () {

    const searchInput =
        document.getElementById("searchConvocatorias");

    const filterButtons =
        document.querySelectorAll(".filter-button");

    const cards =
        document.querySelectorAll(".convocatoria-card");

    const noResults =
        document.getElementById("noResults");


    if (!searchInput) {
        return;
    }


    let currentFilter = "todas";


    function filterConvocatorias() {

        const search =
            searchInput.value
                .toLowerCase()
                .trim();

        let visibleCards = 0;


        cards.forEach(function (card) {

            const status =
                card.dataset.status;

            const text =
                card.dataset.search
                    .toLowerCase();


            const matchesSearch =
                text.includes(search);


            const matchesFilter =
                currentFilter === "todas" ||
                status === currentFilter;


            if (matchesSearch && matchesFilter) {

                card.style.display = "";

                visibleCards++;

            } else {

                card.style.display = "none";

            }

        });


        if (visibleCards === 0) {

            noResults.style.display = "block";

        } else {

            noResults.style.display = "none";

        }

    }


    searchInput.addEventListener(
        "input",
        filterConvocatorias
    );


    filterButtons.forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                filterButtons.forEach(function (btn) {

                    btn.classList.remove("active");

                });


                button.classList.add("active");


                currentFilter =
                    button.dataset.filter;


                filterConvocatorias();

            }
        );

    });

});

// =========================
// DIRECTORIO DE PERSONAS
// =========================

const peopleSearch =
    document.getElementById("searchPeople");

const areaFilter =
    document.getElementById("areaFilter");

const peopleCards =
    document.querySelectorAll(".person-card");

const peopleCount =
    document.getElementById("peopleCount");

const peopleNoResults =
    document.getElementById("peopleNoResults");


if (peopleSearch && areaFilter) {

    function filterPeople() {

        const search =
            peopleSearch.value
                .toLowerCase()
                .trim();

        const selectedArea =
            areaFilter.value
                .toLowerCase();


        let visiblePeople = 0;


        peopleCards.forEach(function (card) {

            const name =
                card.dataset.name.toLowerCase();

            const area =
                card.dataset.area.toLowerCase();

            const position =
                card.dataset.position.toLowerCase();


            const matchesSearch =
                name.includes(search) ||
                area.includes(search) ||
                position.includes(search);


            const matchesArea =
                selectedArea === "todas" ||
                area === selectedArea;


            if (matchesSearch && matchesArea) {

                card.style.display = "";

                visiblePeople++;

            } else {

                card.style.display = "none";

            }

        });


        peopleCount.textContent =
            visiblePeople;


        if (visiblePeople === 0) {

            peopleNoResults.style.display =
                "block";

        } else {

            peopleNoResults.style.display =
                "none";

        }

    }


    peopleSearch.addEventListener(
        "input",
        filterPeople
    );


    areaFilter.addEventListener(
        "change",
        filterPeople
    );

}

/* =========================================================
   MENSAJES
========================================================= */

let currentConversation = "ana";


/* Datos temporales */

const conversationsData = {

    ana: {
        name: "Ana Martínez",
        initials: "AM",
        status: "Disponible",
        statusClass: "available"
    },

    carlos: {
        name: "Carlos Ramírez",
        initials: "CR",
        status: "Disponible",
        statusClass: "available"
    },

    mariana: {
        name: "Mariana López",
        initials: "ML",
        status: "Disponible",
        statusClass: "available"
    },

    jorge: {
        name: "Jorge Hernández",
        initials: "JH",
        status: "Ausente",
        statusClass: "away"
    },

    laura: {
        name: "Laura González",
        initials: "LG",
        status: "Desconectada",
        statusClass: "offline"
    }

};


/* =========================================================
   ABRIR CONVERSACIÓN
========================================================= */

function openConversation(user) {

    currentConversation = user;

    const data = conversationsData[user];

    if (!data) {
        return;
    }

    const chatName = document.getElementById("chatName");
    const chatStatus = document.getElementById("chatStatus");
    const chatAvatar = document.getElementById("chatAvatar");

    if (chatName) {
        chatName.textContent = data.name;
    }

    if (chatStatus) {
        chatStatus.textContent = data.status;

        if (data.statusClass === "available") {
            chatStatus.style.color = "#12B76A";
        } else if (data.statusClass === "away") {
            chatStatus.style.color = "#F79009";
        } else {
            chatStatus.style.color = "#98A2B3";
        }
    }

    if (chatAvatar) {

        chatAvatar.innerHTML = `
            ${data.initials}
            <span class="status-dot ${data.statusClass}"></span>
        `;

    }


    /* Marcar conversación como activa */

    document.querySelectorAll(".conversation-item").forEach(item => {
        item.classList.remove("active");
    });

    const selected = document.querySelector(
        `.conversation-item[data-user="${user}"]`
    );

    if (selected) {

        selected.classList.add("active");

        const unread = selected.querySelector(".unread-badge");

        if (unread) {
            unread.remove();
        }

    }

}


/* =========================================================
   BUSCAR CONVERSACIONES
========================================================= */

const searchConversations =
    document.getElementById("searchConversations");

if (searchConversations) {

    searchConversations.addEventListener("input", function () {

        const search = this.value
            .toLowerCase()
            .trim();

        const conversations =
            document.querySelectorAll(".conversation-item");

        let visible = 0;

        conversations.forEach(conversation => {

            const name =
                conversation.dataset.name.toLowerCase();

            if (name.includes(search)) {

                conversation.style.display = "flex";
                visible++;

            } else {

                conversation.style.display = "none";

            }

        });


        const noConversations =
            document.getElementById("noConversations");

        if (noConversations) {

            noConversations.style.display =
                visible === 0 ? "block" : "none";

        }

    });

}


/* =========================================================
   ENVIAR MENSAJE
========================================================= */

const messageForm =
    document.getElementById("messageForm");

if (messageForm) {

    messageForm.addEventListener("submit", function (event) {

        event.preventDefault();

        const input =
            document.getElementById("messageInput");

        const message =
            input.value.trim();

        if (!message) {
            return;
        }


        const chatMessages =
            document.getElementById("chatMessages");

        if (!chatMessages) {
            return;
        }


        /* Crear mensaje */

        const messageElement =
            document.createElement("div");

        messageElement.className = "message sent";

        messageElement.innerHTML = `
            <div class="message-bubble">
                <p>${escapeHtml(message)}</p>

                <span class="message-time">
                    Ahora
                    <i class="fa-solid fa-check"></i>
                </span>
            </div>
        `;


        chatMessages.appendChild(messageElement);


        /* Limpiar */

        input.value = "";


        /* Scroll automático */

        chatMessages.scrollTop =
            chatMessages.scrollHeight;

    });

}


/* =========================================================
   ARCHIVOS
========================================================= */

const fileInput =
    document.getElementById("fileInput");

if (fileInput) {

    fileInput.addEventListener("change", function () {

        const file = this.files[0];

        if (!file) {
            return;
        }

        const preview =
            document.getElementById("attachmentPreview");

        const name =
            document.getElementById("attachmentName");

        if (preview && name) {

            name.textContent = file.name;

            preview.style.display = "flex";

        }

    });

}


/* =========================================================
   ELIMINAR ARCHIVO
========================================================= */

function removeAttachment() {

    const fileInput =
        document.getElementById("fileInput");

    const preview =
        document.getElementById("attachmentPreview");

    if (fileInput) {
        fileInput.value = "";
    }

    if (preview) {
        preview.style.display = "none";
    }

}


/* =========================================================
   SEGURIDAD BÁSICA PARA MENSAJES
========================================================= */

function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

}

/* =========================================================
   PERFIL
========================================================= */

const editProfileButton =
    document.getElementById("editProfileButton");

const profileModal =
    document.getElementById("profileModal");

const closeProfileModal =
    document.getElementById("closeProfileModal");

const cancelProfileEdit =
    document.getElementById("cancelProfileEdit");


/* Abrir modal */

if (editProfileButton && profileModal) {

    editProfileButton.addEventListener("click", function () {

        profileModal.classList.add("show");

    });

}


/* Cerrar modal */

function closeProfile() {

    if (profileModal) {
        profileModal.classList.remove("show");
    }

}


if (closeProfileModal) {

    closeProfileModal.addEventListener(
        "click",
        closeProfile
    );

}


if (cancelProfileEdit) {

    cancelProfileEdit.addEventListener(
        "click",
        closeProfile
    );

}


/* Cerrar al hacer clic fuera */

if (profileModal) {

    profileModal.addEventListener("click", function (event) {

        if (event.target === profileModal) {
            closeProfile();
        }

    });

}


/* Guardar cambios temporalmente */

const profileForm =
    document.getElementById("profileForm");

if (profileForm) {

    profileForm.addEventListener("submit", function (event) {

        event.preventDefault();

        const name =
            document.getElementById("profileName").value.trim();

        const lastName =
            document.getElementById("profileLastName").value.trim();


        if (!name || !lastName) {

            alert("Por favor completa tu nombre y apellidos.");

            return;

        }


        const identity =
            document.querySelector(".profile-identity h2");

        const mainName =
            document.querySelector(".profile-main .profile-identity h2");

        const infoName =
            document.querySelector(
                ".profile-info-item strong"
            );


        const fullName =
            `${name} ${lastName}`;


        if (identity) {
            identity.textContent = fullName;
        }

        if (mainName) {
            mainName.textContent = fullName;
        }

        if (infoName) {
            infoName.textContent = fullName;
        }


        closeProfile();

        alert("Los cambios se guardaron temporalmente.");

    });

}


/* =========================================================
   ESTADO DE DISPONIBILIDAD
========================================================= */

const availabilityOptions =
    document.querySelectorAll(".availability-option");

if (availabilityOptions.length > 0) {

    availabilityOptions.forEach(option => {

        option.addEventListener("click", function () {

            availabilityOptions.forEach(item => {

                item.classList.remove("active");

                const check =
                    item.querySelector("> i");

                if (check) {
                    check.remove();
                }

            });


            this.classList.add("active");


            const check =
                document.createElement("i");

            check.className =
                "fa-solid fa-check";


            this.appendChild(check);

        });

    });

}

/* =========================
   ADMINISTRACIÓN - PUBLICACIONES
========================= */

document.addEventListener("DOMContentLoaded", function () {

    const publicationModal = document.getElementById("publicationModal");
    const openPublicationModal = document.getElementById("openPublicationModal");
    const closePublicationModal = document.getElementById("closePublicationModal");
    const cancelPublication = document.getElementById("cancelPublication");
    const publicationForm = document.getElementById("publicationForm");

    const publicationSearch = document.getElementById("publicationSearch");
    const publicationTypeFilter = document.getElementById("publicationTypeFilter");
    const publicationStatusFilter = document.getElementById("publicationStatusFilter");

    const publicationGrid = document.getElementById("publicationAdminGrid");
    const emptyState = document.getElementById("publicationsEmptyState");

    const publicationTitle = document.getElementById("publicationTitle");
    const publicationType = document.getElementById("publicationType");
    const publicationContent = document.getElementById("publicationContent");
    const publicationDate = document.getElementById("publicationDate");
    const publicationExpiration = document.getElementById("publicationExpiration");
    const publicationImage = document.getElementById("publicationImage");
    const publicationFile = document.getElementById("publicationFile");
    const publicationStatus = document.getElementById("publicationStatus");

    const publicationPreview = document.getElementById("publicationPreview");

    if (!publicationModal || !publicationForm) {
        return;
    }

    let editingCard = null;

    function openModal() {
        publicationModal.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        publicationModal.classList.remove("active");
        document.body.style.overflow = "";
        publicationForm.reset();
        editingCard = null;

        document.getElementById("publicationModalTitle").textContent =
            "Nueva publicación";

        publicationPreview.innerHTML = `
            <div class="publication-preview-icon">
                <i class="fa-solid fa-image"></i>
            </div>

            <div>
                <strong>Vista previa de imagen</strong>
                <p>La imagen seleccionada aparecerá aquí.</p>
            </div>
        `;
    }

    openPublicationModal.addEventListener("click", openModal);
    closePublicationModal.addEventListener("click", closeModal);
    cancelPublication.addEventListener("click", closeModal);

    publicationModal.addEventListener("click", function (event) {
        if (event.target === publicationModal) {
            closeModal();
        }
    });

    publicationImage.addEventListener("change", function () {

        const file = this.files[0];

        if (!file) {
            return;
        }

        if (!file.type.startsWith("image/")) {
            alert("Selecciona un archivo de imagen válido.");
            this.value = "";
            return;
        }

        const reader = new FileReader();

        reader.onload = function (event) {
            publicationPreview.innerHTML = `
                <div class="publication-preview-icon">
                    <img src="${event.target.result}" alt="Vista previa">
                </div>

                <div>
                    <strong>${file.name}</strong>
                    <p>Imagen seleccionada correctamente.</p>
                </div>
            `;
        };

        reader.readAsDataURL(file);
    });

    function filterPublications() {

        const searchValue = publicationSearch.value.toLowerCase().trim();
        const typeValue = publicationTypeFilter.value;
        const statusValue = publicationStatusFilter.value;

        const cards = publicationGrid.querySelectorAll(
            ".publication-admin-card"
        );

        let visibleCards = 0;

        cards.forEach(function (card) {

            const cardText = card.dataset.search.toLowerCase();
            const cardType = card.dataset.type;
            const cardStatus = card.dataset.status;

            const matchesSearch =
                cardText.includes(searchValue);

            const matchesType =
                typeValue === "all" || cardType === typeValue;

            const matchesStatus =
                statusValue === "all" || cardStatus === statusValue;

            if (matchesSearch && matchesType && matchesStatus) {
                card.style.display = "";
                visibleCards++;
            } else {
                card.style.display = "none";
            }
        });

        emptyState.style.display =
            visibleCards === 0 ? "block" : "none";
    }

    publicationSearch.addEventListener("input", filterPublications);
    publicationTypeFilter.addEventListener("change", filterPublications);
    publicationStatusFilter.addEventListener("change", filterPublications);

    publicationForm.addEventListener("submit", function (event) {

        event.preventDefault();

        const title = publicationTitle.value.trim();
        const type = publicationType.value;
        const content = publicationContent.value.trim();
        const date = publicationDate.value;
        const status = publicationStatus.value;

        if (!title || !type || !content || !date) {
            alert("Completa todos los campos obligatorios.");
            return;
        }

        const formattedDate = new Date(
            date + "T12:00:00"
        ).toLocaleDateString("es-MX", {
            day: "numeric",
            month: "long",
            year: "numeric"
        });

        const statusText =
            status === "published" ? "Publicada" : "Borrador";

        const typeClass = type
            .toLowerCase()
            .replace("ó", "o")
            .replace("í", "i")
            .replace(" ", "-");

        const shortContent =
            content.length > 150
                ? content.substring(0, 150) + "..."
                : content;

        if (editingCard) {

            editingCard.dataset.type = type;
            editingCard.dataset.status = status;
            editingCard.dataset.search =
                `${title} ${content} ${type}`.toLowerCase();

            editingCard.querySelector(".publication-type").textContent =
                type;

            editingCard.querySelector(".publication-type").className =
                `publication-type ${typeClass}`;

            editingCard.querySelector(".publication-status").textContent =
                statusText;

            editingCard.querySelector(".publication-status").className =
                `publication-status ${status}`;

            editingCard.querySelector("h3").textContent = title;
            editingCard.querySelector("p").textContent = shortContent;

            editingCard.querySelector(
                ".publication-admin-meta span:first-child"
            ).innerHTML = `
                <i class="fa-regular fa-calendar"></i>
                ${formattedDate}
            `;

        } else {

            const newCard = document.createElement("article");

            newCard.className = "publication-admin-card";

            newCard.dataset.type = type;
            newCard.dataset.status = status;
            newCard.dataset.search =
                `${title} ${content} ${type}`.toLowerCase();

            newCard.innerHTML = `
                <div class="publication-admin-card-top">
                    <span class="publication-type ${typeClass}">
                        ${type}
                    </span>

                    <span class="publication-status ${status}">
                        ${statusText}
                    </span>
                </div>

                <div class="publication-admin-icon">
                    <i class="fa-solid fa-file-lines"></i>
                </div>

                <h3>${escapePublicationHtml(title)}</h3>

                <p>${escapePublicationHtml(shortContent)}</p>

                <div class="publication-admin-meta">
                    <span>
                        <i class="fa-regular fa-calendar"></i>
                        ${formattedDate}
                    </span>

                    <span>
                        <i class="fa-regular fa-user"></i>
                        Administración
                    </span>
                </div>

                <div class="publication-admin-actions">
                    <button class="secondary-button edit-publication">
                        <i class="fa-solid fa-pen"></i>
                        Editar
                    </button>

                    <button class="danger-button delete-publication">
                        <i class="fa-solid fa-trash"></i>
                        Eliminar
                    </button>
                </div>
            `;

            publicationGrid.prepend(newCard);
        }

        closeModal();
        filterPublications();

        alert(
            editingCard
                ? "Publicación actualizada correctamente."
                : "Publicación guardada temporalmente."
        );
    });

    function escapePublicationHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    publicationGrid.addEventListener("click", function (event) {

        const editButton = event.target.closest(".edit-publication");
        const deleteButton = event.target.closest(".delete-publication");

        if (editButton) {

            editingCard = editButton.closest(
                ".publication-admin-card"
            );

            const title = editingCard.querySelector("h3").textContent;
            const content = editingCard.querySelector("p").textContent;
            const type = editingCard.dataset.type;

            publicationTitle.value = title;
            publicationContent.value = content;
            publicationType.value = type;
            publicationStatus.value = editingCard.dataset.status;

            document.getElementById("publicationModalTitle").textContent =
                "Editar publicación";

            openModal();
        }

        if (deleteButton) {

            const card = deleteButton.closest(
                ".publication-admin-card"
            );

            const title = card.querySelector("h3").textContent;

            const confirmed = confirm(
                `¿Deseas eliminar la publicación "${title}"?`
            );

            if (confirmed) {
                card.remove();
                filterPublications();
                alert("Publicación eliminada temporalmente.");
            }
        }

    });

});