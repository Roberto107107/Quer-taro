/* ==========================================
   BUSCADOR GLOBAL
   PRONTUARIO DIGITAL DE LA CONCENTRADORA
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    const buscador = document.getElementById("busqueda");
    const contenedorResultados =
        document.getElementById("resultadosBusqueda");

    if (!buscador || !contenedorResultados) {
        return;
    }


    /* ==========================================
       ÍNDICE GENERAL
    ========================================== */

    const indiceBusqueda = [

        /* ======================================
           COMPRAS
        ====================================== */

        {
            categoria: "Compras",
            titulo: "Gestión y seguimiento de Compras",
            descripcion:
                "Recepción, análisis, integración, trámite y seguimiento de requerimientos de adquisición.",
            palabras:
                "compras compra adquisicion adquisición requerimiento bienes servicios solicitud",
            url: "paginas/compras.html"
        },

        {
            categoria: "Compras",
            titulo: "Requerimientos de adquisición",
            descripcion:
                "Recepción y revisión de requerimientos de bienes o servicios.",
            palabras:
                "requerimiento solicitud bienes servicios documentacion documentación",
            url: "paginas/compras.html#requisitos"
        },

        {
            categoria: "Compras",
            titulo: "Orden de compra",
            descripcion:
                "Seguimiento de la orden de compra posterior a la adjudicación.",
            palabras:
                "orden compra adjudicacion adjudicación proveedor fallo",
            url: "paginas/compras.html#procedimiento"
        },

        {
            categoria: "Compras",
            titulo: "Proveedor adjudicado",
            descripcion:
                "Comunicación y seguimiento con el proveedor adjudicado.",
            palabras:
                "proveedor adjudicado entrega bienes servicios orden compra",
            url: "paginas/compras.html#procedimiento"
        },

        {
            categoria: "Compras",
            titulo: "Fallo de adquisición",
            descripcion:
                "Seguimiento del procedimiento hasta la emisión del fallo correspondiente.",
            palabras:
                "fallo adquisicion adquisición procedimiento adjudicacion adjudicación",
            url: "paginas/compras.html#procedimiento"
        },

        {
            categoria: "Compras",
            titulo: "Garantías",
            descripcion:
                "Seguimiento de garantías y su liberación cuando resulte aplicable.",
            palabras:
                "garantia garantía garantias garantías liberacion liberación proveedor",
            url: "paginas/compras.html#procedimiento"
        },

        {
            categoria: "Compras",
            titulo: "Diagrama de Compras",
            descripcion:
                "Consulta el flujo de gestión y seguimiento del procedimiento de Compras.",
            palabras:
                "diagrama flujo compras procedimiento proceso",
            url: "paginas/compras.html#diagrama"
        },


        /* ======================================
           INVENTARIO
        ====================================== */

        {
            categoria: "Inventario",
            titulo: "Recepción, control y entrega de bienes",
            descripcion:
                "Control de los bienes desde su recepción hasta su entrega.",
            palabras:
                "inventario bienes recepcion recepción control entrega",
            url: "paginas/inventario.html"
        },

        {
            categoria: "Inventario",
            titulo: "Recepción de bienes",
            descripcion:
                "Coordinación y verificación física y documental de los bienes recibidos.",
            palabras:
                "recepcion recepción bienes proveedor entrega cantidad caracteristicas características",
            url: "paginas/inventario.html#procedimiento"
        },

        {
            categoria: "Inventario",
            titulo: "Números de serie",
            descripcion:
                "Identificación y registro de números de serie cuando corresponda.",
            palabras:
                "numero número numeros números serie serial bienes identificacion identificación",
            url: "paginas/inventario.html#procedimiento"
        },

        {
            categoria: "Inventario",
            titulo: "Vale de entrada y SIAFEQ",
            descripcion:
                "Gestión del vale de entrada en SIAFEQ cuando resulte aplicable.",
            palabras:
                "siafeq vale entrada bienes inventario sistema",
            url: "paginas/inventario.html#procedimiento"
        },

        {
            categoria: "Inventario",
            titulo: "Etiquetado patrimonial",
            descripcion:
                "Coordinación del etiquetado de bienes sujetos a control patrimonial.",
            palabras:
                "etiquetado etiqueta patrimonio patrimonial control bienes",
            url: "paginas/inventario.html#procedimiento"
        },

        {
            categoria: "Inventario",
            titulo: "Dirección de Control Patrimonial",
            descripcion:
                "Coordinación en las actividades que corresponden al control patrimonial de los bienes.",
            palabras:
                "direccion dirección control patrimonial altas bajas movimientos bienes inventario",
            url: "paginas/inventario.html#validaciones"
        },

        {
            categoria: "Inventario",
            titulo: "Resguardo de bienes",
            descripcion:
                "Gestión o actualización del resguardo del bien cuando corresponda.",
            palabras:
                "resguardo resguardante bienes responsable inventario",
            url: "paginas/inventario.html#procedimiento"
        },

        {
            categoria: "Inventario",
            titulo: "Diagrama de Inventario",
            descripcion:
                "Consulta el flujo de recepción, control y entrega de bienes.",
            palabras:
                "diagrama flujo inventario bienes recepcion recepción entrega",
            url: "paginas/inventario.html#diagrama"
        },


        /* ======================================
           DICTÁMENES TÉCNICOS
        ====================================== */

        {
            categoria: "Dictámenes Técnicos",
            titulo: "Gestión y seguimiento de Dictámenes Técnicos",
            descripcion:
                "Recepción, registro, control y seguimiento de solicitudes de Dictamen Técnico.",
            palabras:
                "dictamen dictamenes dictámenes tecnico técnico solicitud seguimiento",
            url: "paginas/dictamenes.html"
        },

        {
            categoria: "Dictámenes Técnicos",
            titulo: "Solicitud de Dictamen Técnico",
            descripcion:
                "Recepción y revisión documental de solicitudes de Dictamen Técnico.",
            palabras:
                "solicitud dictamen tecnico técnico documentacion documentación soporte",
            url: "paginas/dictamenes.html#requisitos"
        },

        {
            categoria: "Dictámenes Técnicos",
            titulo: "Registro en SIGNA",
            descripcion:
                "Registro o seguimiento mediante SIGNA cuando corresponda.",
            palabras:
                "signa registro seguimiento documentos digitales dictamen",
            url: "paginas/dictamenes.html#procedimiento"
        },

        {
            categoria: "Dictámenes Técnicos",
            titulo: "Firmas y autorización",
            descripcion:
                "Gestión de las firmas necesarias cuando corresponda.",
            palabras:
                "firma firmas autorizacion autorización vobo visto bueno dictamen",
            url: "paginas/dictamenes.html#procedimiento"
        },

        {
            categoria: "Dictámenes Técnicos",
            titulo: "Notificación y acuse",
            descripcion:
                "Envío del resultado y registro del acuse de recepción cuando aplique.",
            palabras:
                "notificacion notificación envio envío acuse recepcion recepción dictamen",
            url: "paginas/dictamenes.html#procedimiento"
        },

        {
            categoria: "Dictámenes Técnicos",
            titulo: "Diagrama de Dictámenes Técnicos",
            descripcion:
                "Consulta el flujo de gestión y seguimiento de Dictámenes Técnicos.",
            palabras:
                "diagrama flujo dictamen dictamenes dictámenes tecnico técnico",
            url: "paginas/dictamenes.html#diagrama"
        },


        /* ======================================
           FORMATOS
        ====================================== */

        {
            categoria: "Formatos y Anexos",
            titulo: "Formato Solicitud de Bienes DGDI",
            descripcion:
                "Formato relacionado con la solicitud y gestión de bienes.",
            palabras:
                "formato solicitud bienes dgdi compras inventario",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Formato de Resguardo",
            descripcion:
                "Documento relacionado con la asignación y responsabilidad sobre bienes.",
            palabras:
                "formato resguardo bienes inventario responsable",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Formato de Resguardo Parcial",
            descripcion:
                "Formato relacionado con el control parcial de bienes bajo resguardo.",
            palabras:
                "formato resguardo parcial bienes inventario",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Formato de Cambio de Resguardante",
            descripcion:
                "Documento para la actualización del responsable de bienes.",
            palabras:
                "formato cambio resguardante responsable bienes inventario",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Formato Baja de Bienes DGDI",
            descripcion:
                "Formato asociado a la documentación para baja de bienes.",
            palabras:
                "formato baja bienes dgdi inventario",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Solicitud de Dictamen de Baja de Equipos",
            descripcion:
                "Formato relacionado con el dictamen de baja de equipos.",
            palabras:
                "formato solicitud dictamen baja equipos inventario",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Solicitud de Dictamen de Autorización de Presupuesto",
            descripcion:
                "Formato relacionado con la solicitud de Dictamen Técnico correspondiente.",
            palabras:
                "formato dictamen autorizacion autorización presupuesto compras",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Anexo para Adquisición de Equipo de Cómputo",
            descripcion:
                "Documento complementario relacionado con la adquisición de equipo de cómputo.",
            palabras:
                "anexo adquisicion adquisición equipo computo cómputo compras dictamen",
            url: "paginas/formatos.html"
        },

        {
            categoria: "Formatos y Anexos",
            titulo: "Formato Anexo de VoBo",
            descripcion:
                "Documento complementario relacionado con el Visto Bueno.",
            palabras:
                "formato anexo vobo visto bueno dictamen",
            url: "paginas/formatos.html"
        },


        /* ======================================
           NORMATIVIDAD
        ====================================== */

        {
            categoria: "Marco Normativo",
            titulo: "Marco Jurídico y Normativo",
            descripcion:
                "Consulta la normatividad relacionada con los procedimientos de la Concentradora.",
            palabras:
                "normatividad normativa marco juridico jurídico leyes reglamentos acuerdo",
            url: "paginas/normatividad.html"
        },

        {
            categoria: "Marco Normativo",
            titulo: "Manejo, Administración y Ejercicio del Gasto Público",
            descripcion:
                "Instrumento normativo principal considerado en el Manual de Procedimientos.",
            palabras:
                "acuerdo manual manejo administracion administración ejercicio gasto publico público",
            url: "paginas/normatividad.html"
        },

        {
            categoria: "Marco Normativo",
            titulo: "Clasificador por Objeto del Gasto",
            descripcion:
                "Consulta la referencia al COG dentro del marco normativo.",
            palabras:
                "cog clasificador objeto gasto presupuesto presupuestal",
            url: "paginas/normatividad.html"
        },

        {
            categoria: "Marco Normativo",
            titulo: "Control patrimonial",
            descripcion:
                "Referencia normativa relacionada con altas, bajas, movimientos e inventario institucional.",
            palabras:
                "control patrimonial altas bajas movimientos inventario bienes",
            url: "paginas/normatividad.html"
        },


        /* ======================================
           GLOSARIO
        ====================================== */

        {
            categoria: "Glosario",
            titulo: "COG",
            descripcion:
                "Clasificador por Objeto del Gasto.",
            palabras:
                "cog clasificador objeto gasto",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "Dictamen Técnico",
            descripcion:
                "Consulta la definición institucional de Dictamen Técnico.",
            palabras:
                "dictamen tecnico técnico definicion definición",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "Orden de compra",
            descripcion:
                "Consulta la definición de orden de compra.",
            palabras:
                "orden compra definicion definición",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "Proveedor",
            descripcion:
                "Consulta la definición de proveedor.",
            palabras:
                "proveedor definicion definición",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "Requerimiento",
            descripcion:
                "Consulta la definición de requerimiento.",
            palabras:
                "requerimiento solicitud definicion definición",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "Resguardo",
            descripcion:
                "Consulta la definición institucional de resguardo.",
            palabras:
                "resguardo bienes responsable definicion definición",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "SIAFEQ",
            descripcion:
                "Sistema Integrado de Administración Financiera del Estado de Querétaro.",
            palabras:
                "siafeq sistema integrado administracion administración financiera vale entrada",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "SIGNA",
            descripcion:
                "Sistema Integral de Gestión y Autenticación de Documentos Digitales.",
            palabras:
                "signa sistema integral gestion gestión autenticacion autenticación documentos digitales",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "Trazabilidad",
            descripcion:
                "Consulta la definición de trazabilidad dentro de los procedimientos.",
            palabras:
                "trazabilidad seguimiento documentos registros responsables",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "Vale de entrada",
            descripcion:
                "Consulta la definición de vale de entrada.",
            palabras:
                "vale entrada bienes siafeq definicion definición",
            url: "paginas/glosario.html"
        },

        {
            categoria: "Glosario",
            titulo: "VoBo",
            descripcion:
                "Visto Bueno. Consulta su definición dentro del Manual.",
            palabras:
                "vobo visto bueno validacion validación conformidad",
            url: "paginas/glosario.html"
        }

    ];


    /* ==========================================
       NORMALIZAR TEXTO
    ========================================== */

    function normalizar(texto) {

        return texto
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();

    }


    /* ==========================================
       BUSCAR
    ========================================== */

    function realizarBusqueda() {

        const consulta = normalizar(buscador.value);

        contenedorResultados.innerHTML = "";


        /* SIN TEXTO */

        if (consulta.length < 2) {

            contenedorResultados.classList.remove("activo");

            return;

        }


        const palabrasConsulta =
            consulta
                .split(/\s+/)
                .filter(Boolean);


        /* ======================================
           CALCULAR COINCIDENCIAS
        ====================================== */

        const resultados = indiceBusqueda
            .map(item => {

                const contenido = normalizar(
                    item.titulo + " " +
                    item.descripcion + " " +
                    item.palabras + " " +
                    item.categoria
                );


                let puntuacion = 0;


                palabrasConsulta.forEach(palabra => {

                    if (contenido.includes(palabra)) {
                        puntuacion++;
                    }

                });


                /*
                   Prioridad adicional cuando
                   el título contiene exactamente
                   la búsqueda.
                */

                if (
                    normalizar(item.titulo)
                        .includes(consulta)
                ) {

                    puntuacion += 3;

                }


                return {
                    ...item,
                    puntuacion
                };

            })
            .filter(item =>
                item.puntuacion > 0
            )
            .sort((a, b) =>
                b.puntuacion - a.puntuacion
            );


        /* ======================================
           SIN RESULTADOS
        ====================================== */

        if (resultados.length === 0) {

            contenedorResultados.innerHTML = `

                <div class="busqueda-sin-resultados">

                    <strong>
                        No se encontraron resultados
                    </strong>

                    <p>
                        Intenta buscar otro término,
                        por ejemplo:
                        <b>resguardo</b>,
                        <b>SIAFEQ</b>,
                        <b>proveedor</b> o
                        <b>dictamen</b>.
                    </p>

                </div>

            `;

            contenedorResultados.classList.add("activo");

            return;

        }


        /* ======================================
           ENCABEZADO
        ====================================== */

        const encabezado =
            document.createElement("div");

        encabezado.className =
            "busqueda-encabezado";

        encabezado.innerHTML = `

            <span>
                ${resultados.length}
                ${
                    resultados.length === 1
                        ? "resultado"
                        : "resultados"
                }
            </span>

            <button
                type="button"
                id="cerrarBusqueda"
            >
                ×
            </button>

        `;

        contenedorResultados.appendChild(
            encabezado
        );


        /* ======================================
           MOSTRAR RESULTADOS
        ====================================== */

        resultados
            .slice(0, 8)
            .forEach(item => {

                const enlace =
                    document.createElement("a");

                enlace.href = item.url;

                enlace.className =
                    "resultado-global";


                enlace.innerHTML = `

                    <div class="resultado-info">

                        <span class="resultado-categoria">
                            ${item.categoria}
                        </span>

                        <h3>
                            ${item.titulo}
                        </h3>

                        <p>
                            ${item.descripcion}
                        </p>

                    </div>

                    <span class="resultado-flecha">
                        →
                    </span>

                `;


                contenedorResultados.appendChild(
                    enlace
                );

            });


        /*
           Si existen más de 8 resultados,
           indicamos que hay más coincidencias.
        */

        if (resultados.length > 8) {

            const restante =
                document.createElement("div");

            restante.className =
                "resultados-restantes";

            restante.textContent =
                `+ ${resultados.length - 8} coincidencias adicionales. Refina tu búsqueda para encontrarlas.`;

            contenedorResultados.appendChild(
                restante
            );

        }


        contenedorResultados.classList.add(
            "activo"
        );


        /* CERRAR */

        const cerrar =
            document.getElementById(
                "cerrarBusqueda"
            );

        if (cerrar) {

            cerrar.addEventListener(
                "click",
                cerrarResultados
            );

        }

    }


    /* ==========================================
       CERRAR RESULTADOS
    ========================================== */

    function cerrarResultados() {

        contenedorResultados.classList.remove(
            "activo"
        );

        contenedorResultados.innerHTML = "";

    }


    /* ==========================================
       EVENTOS
    ========================================== */

    buscador.addEventListener(
        "input",
        realizarBusqueda
    );


    buscador.addEventListener(
        "keydown",
        event => {

            if (event.key === "Escape") {

                buscador.value = "";

                cerrarResultados();

            }

        }
    );


    /*
       Si existe un botón de búsqueda
       en index.html, también funcionará.
    */

    const botonBuscar =
        document.getElementById("btnBuscar");


    if (botonBuscar) {

        botonBuscar.addEventListener(
            "click",
            realizarBusqueda
        );

    }

});