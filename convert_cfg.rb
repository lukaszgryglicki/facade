require 'pry'
require 'scanf'

def convert_cfg(fin, fout)
  affs = []
  File.readlines(fin).each do |line|
    # GroupMap cncf-config/groups/intel Intel
    next unless line.include?('GroupMap')
    fn, employer = line.scanf('GroupMap %s %s')
    next unless fn && employer
    # puts "File: #{fn} --> employer: #{employer}"
    File.readlines(fn).each do |line|
      affs << [line.strip, employer]
    end
  end

  # Here is a set of mappings of domain names onto employer names.
  File.open(fout, 'w') do |file|
    file.write("# Here is a set of mappings of domain names onto employer names.\n")
    affs.each do |aff|
      file.write("#{aff[0]} #{aff[1]}\n")
    end
  end

end

if ARGV.size < 2
  puts "Missing arguments: cncf-config/gitdm.config-cncf cncf-config/group-map"
  exit(1)
end

convert_cfg(ARGV[0], ARGV[1])
