clearFilesystem();
initFilesystem();

QUnit.test( "Filesystem", function( assert ) {
  addFile("Foo.txt", "This is the contents");
  addFile("Moo.txt", "This is the contents2");
  assert.ok(listFiles().length == 2);

  var thefile = getFile("Foo.txt");
  assert.equal(getFile("Foo.txt").contents, "This is the contents")
  assert.equal(getFile("Moo.txt").contents, "This is the contents2")

  deleteFile("Foo.txt")
  assert.ok(listFiles().length == 1);
  assert.throws(getFile.bind(this, "Foo.txt"), Error);

  deleteFile("Moo.txt")
  assert.ok(listFiles().length == 0);
});
