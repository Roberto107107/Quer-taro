document.addEventListener("DOMContentLoaded", () => {

    const buscador =
        document.getElementById("buscarTermino");

    const tarjetas =
        document.querySelectorAll(".termino-card");

    const contador =
        document.getElementById("contadorTerminos");

    const sinResultados =
        document.getElementById("sinTerminos");


    function normalizarTexto(texto) {

        return texto
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");

    }


    function buscar() {

        const texto =
            normalizarTexto(
                buscador.value.trim()
            );

        let visibles = 0;


        tarjetas.forEach(tarjeta => {

            const termino =
                normalizarTexto(
                    tarjeta.dataset.termino || ""
                );

            const contenido =
                normalizarTexto(
                    tarjeta.textContent
                );


            const coincide =
                texto === "" ||
                termino.includes(texto) ||
                contenido.includes(texto);


            if (coincide) {

                tarjeta.style.display = "";
                visibles++;

            } else {

                tarjeta.style.display = "none";

            }

        });


        contador.textContent =
            visibles === 1
                ? "1 término disponible"
                : `${visibles} términos disponibles`;


        sinResultados.style.display =
            visibles === 0
                ? "block"
                : "none";

    }


    buscador.addEventListener(
        "input",
        buscar
    );

});