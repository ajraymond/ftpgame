var File = function(filename, contents) {
  this.name = filename;
  this.contents = contents;
  this.type = 'file';
};

File.prototype.toString = function() {
  return JSON.stringify({name: this.name, contents: this.contents, type: this.type});
};

/////////

var Filesystem = function(prefix) {
  this.prefix = prefix?prefix:"";

  if (localStorage.getItem(this._getFsName()) === null) {
    localStorage.setItem(this._getFsName(), JSON.stringify([]));
  }
};

Filesystem.prototype._getFsName = function(name) {
  var n = "filesystem" + (this.prefix?("_"+this.prefix):"") + (name?("_"+name):"");
  return n;
};

Filesystem.prototype.deleteFile = function(filename) {
  var filesystem = JSON.parse(localStorage.getItem(this._getFsName()));

  if (filesystem.indexOf(filename) == -1) {
    throw Error("File doesn't exist");
  }

  filesystem.splice(filesystem.indexOf(filename),1);
  localStorage.setItem(this._getFsName(), JSON.stringify(filesystem));

  localStorage.removeItem(this._getFsName(filename));
};

Filesystem.prototype.listFiles = function() {
  var filesystem = JSON.parse(localStorage.getItem(this._getFsName()));

  return filesystem;
};

Filesystem.prototype.addFile = function(filename, contents) {
  var filesystem = JSON.parse(localStorage.getItem(this._getFsName()));

  if (filesystem.indexOf(filename) == -1) {
    filesystem.push(filename);
    localStorage.setItem(this._getFsName(), JSON.stringify(filesystem));
  }
  localStorage.setItem(this._getFsName(filename), contents);
};

Filesystem.prototype.getFile = function(filename) {
  var fileContents = localStorage.getItem(this._getFsName(filename));
  if (fileContents === null) {
    throw Error("File doesn't exist");
  }
  return new File(filename, fileContents);
};

Filesystem.prototype.getAllFiles = function() {
  var filesystem = JSON.parse(localStorage.getItem(this._getFsName()));
  var allFiles = [];
  var that = this;
  filesystem.forEach(function(f) {
    var fileContents = localStorage.getItem(that._getFsName(f));
    allFiles.push(new File(f, fileContents));
  });
  return allFiles;
};

