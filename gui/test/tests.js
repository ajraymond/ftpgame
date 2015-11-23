QUnit.test( "Filesystem", function( assert ) {
  var fs = new Filesystem();

  fs.addFile("Foo.txt", "This is the contents");
  fs.addFile("Moo.txt", "This is the contents2");
  assert.ok(fs.listFiles().length == 2);

  var thefile = fs.getFile("Foo.txt");
  assert.equal(fs.getFile("Foo.txt").contents, "This is the contents")
  assert.equal(fs.getFile("Moo.txt").contents, "This is the contents2")

  fs.deleteFile("Foo.txt")
  assert.ok(fs.listFiles().length == 1);
  assert.throws(fs.getFile.bind(this, "Foo.txt"), Error);

  fs.deleteFile("Moo.txt")
  assert.ok(fs.listFiles().length == 0);
});

QUnit.test( "Filesystem with prefix", function( assert ) {
  var fs = new Filesystem("myprefix");

  fs.addFile("Foo.txt", "This is the contents");
  fs.addFile("Moo.txt", "This is the contents2");
  assert.ok(fs.listFiles().length == 2);

  var thefile = fs.getFile("Foo.txt");
  assert.equal(fs.getFile("Foo.txt").contents, "This is the contents")
  assert.equal(fs.getFile("Moo.txt").contents, "This is the contents2")

  fs.deleteFile("Foo.txt")
  assert.ok(fs.listFiles().length == 1);
  assert.throws(fs.getFile.bind(this, "Foo.txt"), Error);

  fs.deleteFile("Moo.txt")
  assert.ok(fs.listFiles().length == 0);
});
