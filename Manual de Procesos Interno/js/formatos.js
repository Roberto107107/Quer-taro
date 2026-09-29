document.addEventListener("DOMContentLoaded", () => {

    const buscador =
        document.getElementById("buscarFormato");

    const botones =
        document.querySelectorAll(".filtro-formato");

    const tarjetas =
        document.querySelectorAll(".tarjeta-formato");

    const contador =
        document.getElementById("contadorFormatos");

    const sinResultados =
        document.getElementById("sinFormatos");


    let categoriaActual = "todos";


    function normalizarTexto(texto) {

        return texto
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");

    }


    function filtrarFormatos() {

        const texto =
            normalizarTexto(buscador.value.trim());

        let visibles = 0;


        tarjetas.forEach(tarjeta => {

            const nombre =
                normalizarTexto(
                    tarjeta.dataset.nombre || ""
                );

            const contenido =
                normalizarTexto(
                    tarjeta.textContent
                );

            const categorias =
                (tarjeta.dataset.categoria || "")
                .split(" ");


            const coincideCategoria =
                categoriaActual === "todos" ||
                categorias.includes(categoriaActual);


            const coincideTexto =
                texto === "" ||
                nombre.includes(texto) ||
                contenido.includes(texto);


            if (coincideCategoria && coincideTexto) {

                tarjeta.style.display = "";
                visibles++;

            } else {

                tarjeta.style.display = "none";

            }

        });


        contador.textContent =
            visibles === 1
                ? "1 documento disponible"
                : `${visibles} documentos disponibles`;


        sinResultados.style.display =
            visibles === 0 ? "block" : "none";

    }


    /* BUSCADOR */

    buscador.addEventListener(
        "input",
        filtrarFormatos
    );


    /* FILTROS */

    botones.forEach(boton => {

        boton.addEventListener("click", () => {

            botones.forEach(b => {
                b.classList.remove("activo");
            });


            boton.classList.add("activo");


            categoriaActual =
                boton.dataset.filtro;


            filtrarFormatos();

        });

    });


});