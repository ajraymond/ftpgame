$(document).ready(function(){

    function updateFileLists() {
        var template = $.templates("#fileTemplate");
        $("#local").html(template.render(localData));
        $("#remote").html(template.render(remoteData));
        $('tr:not(:has(th))').click(function() {
            $(this).closest("tr").siblings().removeClass("highlighted");
            $(this).toggleClass("highlighted");
        })
    }
      
    var localData = [
        { "id": 0, "filename": "file1.txt" },
        { "id": 1, "filename": "file2.txt" },
        { "id": 2, "filename": "file3.html" },
    ];

    var remoteData = [];
    for (i=0; i < 200; i++) {
        remoteData.push( { "id": i, "filename": "file"+i+".txt" })
    }  
    
    updateFileLists();
});


