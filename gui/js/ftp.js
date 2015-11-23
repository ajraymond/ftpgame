$(document).ready(function(){
  var fs = new Filesystem("local");

  function updateFileLists() {
    var template = $.templates("#fileTemplate");
    $("#local").html(template.render(fs.getAllFiles()));
    $("#remote").html(template.render(remoteData));
  }

  var remoteData = [];
  for (i=0; i < 200; i++) {
    remoteData.push( { "name": i, "contents": "file"+i+".txt" });
  }

  updateFileLists();

  var opts = {dragClass:"bilboDraggins",
              on: {
              load: function(e, file) {
                fs.addFile(file.name, e.target.result);
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

  $('.container').contextmenu({
    target: '#context-menu',
    before: function (e) {
      e.preventDefault();
      if (e.target.tagName != 'TD') {
        this.closemenu();
        return false;
      }
      return true;
    }
  });
});

