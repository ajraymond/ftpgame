$(document).ready(function(){

    function updateFileLists() {
      var template = $.templates("#fileTemplate");
      $("#local").html(template.render(getAllFiles()));
      $("#remote").html(template.render(remoteData));

      $('tr:not(:has(th))').click(function() {
        $(this).closest("tr").siblings().removeClass("highlighted");
        $(this).toggleClass("highlighted");
      })
    }

    var remoteData = [];
    for (i=0; i < 200; i++) {
      remoteData.push( { "name": i, "contents": "file"+i+".txt" })
    }

    updateFileLists();

    var opts = {dragClass:"bilboDraggins",
                on: {
                load: function(e, file) {
                  addFile(file.name, e.target.result);
                  updateFileLists();
                  }
               }
    };
    $("#dropzone").fileReaderJS(opts);
    $("body").fileClipboard(opts);


    $("tbody tr").on("dblclick", function(){
      console.log("Clicked!");
      $("#myModal").modal();
    });

    $(".deleteaction").on("click", function(){
      alert("Clicked on row " + $(this).closest("tbody").children("tr").index($(this).closest("tr")));
    });

    //filesystem tests
    console.log("List of files:", listFiles());
    console.log("Adding Foo.txt");
    addFile("Foo.txt", "This is the contents");
    addFile("Moo.txt", "This is the contents2");
    console.log("List of files:", listFiles());
    console.log("All files:", getAllFiles());
    var thefile = getFile("Foo.txt");
    console.log("Foo.txt object:", thefile.toString());
    thefile = getFile("Moo.txt");
    console.log("Moo.txt object:", thefile.toString());
    console.log("Deleting Foo.txt");
    deleteFile("Foo.txt")
    console.log("List of files:", listFiles());
    try {
     console.log("Getting file Foo.txt again");
     contents = getFile("Foo.txt");
    } catch(e) {
      console.log("Caught that... doesn't exist! Wheeh!");
    }
    console.log("List of files:", listFiles());
});


