var clearFilesystem = function() {
  localstorage.clear();
}

var initFilesystem = function() {
  if (localStorage.getItem("filesystem")== null) {
    localStorage.setItem("filesystem", JSON.stringify([]));
  }
}

var deleteFile = function(filename) {
  var filesystem = JSON.parse(localStorage.getItem("filesystem"));

  if (filesystem.indexOf(filename) == -1) {
    throw Error("File doesn't exist");
  }

  filesystem.splice(filesystem.indexOf(filename),1);
  localStorage.setItem("filesystem", JSON.stringify(filesystem));

  localStorage.removeItem(filename);
}

var listFiles = function() {
  var filesystem = JSON.parse(localStorage.getItem("filesystem"));

  return filesystem;
}

var saveFile = function(filename, contents) {
  var filesystem = JSON.parse(localStorage.getItem("filesystem"));

  if (filesystem.indexOf(filename) == -1) {
    filesystem.push(filename);
    localStorage.setItem("filesystem", JSON.stringify(filesystem));
  }
  localStorage.setItem(filename, contents);
}

var getFile = function(filename) {
  var fileContents = localStorage.getItem(filename);
  if (fileContents == null) {
    throw Error("File doesn't exist");
  }
  return fileContents;
}

initFilesystem();
