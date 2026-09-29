document.addEventListener("DOMContentLoaded", () => {
    console.log("Prontuario Digital de la Concentradora iniciado.");
});

function abrirDiagrama(ruta) {

    const visor = document.getElementById("visorDiagrama");
    const imagen = document.getElementById("imagenDiagramaAmpliada");

    if (!visor || !imagen) {
        return;
    }

    imagen.src = ruta;

    visor.classList.add("activo");

    document.body.style.overflow = "hidden";
}


function cerrarDiagrama() {

    const visor = document.getElementById("visorDiagrama");

    if (!visor) {
        return;
    }

    visor.classList.remove("activo");

    document.body.style.overflow = "";
}


/* Cerrar con ESC */

document.addEventListener("keydown", (event) => {

    if (event.key === "Escape") {
        cerrarDiagrama();
    }

});


/* Cerrar al hacer clic fuera del diagrama */

document.addEventListener("click", (event) => {

    const visor = document.getElementById("visorDiagrama");

    if (
        visor &&
        visor.classList.contains("activo") &&
        event.target === visor
    ) {
        cerrarDiagrama();
    }

});