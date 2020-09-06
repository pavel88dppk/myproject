//define some functions

//menu toggle function
function togglesidebar() {
    document.getElementById("sidebar").classList.toggle('active');
}


var table = document.getElementById("table"),
    rIndex;
            
for (var i = 2; i < table.rows.length; i++) {
    table.rows[i].onclick = function() {
        rIndex = this.rowIndex;
        console.log(rIndex);
    };
}

