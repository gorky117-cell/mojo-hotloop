
/tmp/hotloop-provenance/final-performance/baseline-1/fast.so:     file format elf64-x86-64


Disassembly of section .text:

00000000000018d0 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])>:
    18d0:	push   %rax
    18d1:	mov    %rdi,%rax
    18d4:	test   %rsi,%rsi
    18d7:	jle    1a3a <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x16a>
    18dd:	vmovsd 0xe71b(%rip),%xmm3        # 10000 <_fini+0x9f0>
    18e5:	vxorpd %xmm4,%xmm4,%xmm4
    18e9:	vucomisd %xmm4,%xmm1
    18ed:	jbe    19da <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x10a>
    18f3:	vsubsd %xmm2,%xmm3,%xmm2
    18f7:	vsubsd %xmm1,%xmm3,%xmm1
    18fb:	mov    $0x1,%dil
    18fe:	mov    $0x2a,%ecx
    1903:	xor    %edx,%edx
    1905:	vmovsd 0xe6fb(%rip),%xmm5        # 10008 <_fini+0x9f8>
    190d:	vmovsd 0xe6fb(%rip),%xmm6        # 10010 <_fini+0xa00>
    1915:	vmovsd 0xe6fb(%rip),%xmm7        # 10018 <_fini+0xa08>
    191d:	vmovapd %xmm3,%xmm10
    1921:	vxorpd %xmm8,%xmm8,%xmm8
    1926:	vmovapd %xmm0,%xmm9
    192a:	jmp    193d <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x6d>
    192c:	nopl   0x0(%rax)
    1930:	vmovapd %xmm9,%xmm0
    1934:	dec    %rsi
    1937:	je     1a2c <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x15c>
    193d:	imul   $0x19660d,%ecx,%ecx
    1943:	add    $0x3c6ef35f,%ecx
    1949:	vcvtsi2sd %rcx,%xmm15,%xmm11
    194e:	vmulsd %xmm5,%xmm11,%xmm11
    1952:	vaddsd %xmm6,%xmm11,%xmm11
    1956:	vmulsd %xmm7,%xmm11,%xmm11
    195a:	vaddsd %xmm3,%xmm11,%xmm11
    195e:	vmulsd %xmm11,%xmm9,%xmm9
    1963:	test   $0x1,%dil
    1967:	je     19a0 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0xd0>
    1969:	mov    $0x1,%dil
    196c:	vucomisd %xmm0,%xmm9
    1970:	ja     1930 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x60>
    1972:	vmulsd %xmm0,%xmm1,%xmm11
    1976:	vucomisd %xmm9,%xmm11
    197b:	jb     1934 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x64>
    197d:	vmulsd %xmm9,%xmm10,%xmm8
    1982:	vmulsd %xmm2,%xmm8,%xmm8
    1986:	mov    $0x5,%edx
    198b:	vxorpd %xmm10,%xmm10,%xmm10
    1990:	xor    %edi,%edi
    1992:	jmp    1934 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x64>
    1994:	data16 data16 cs nopw 0x0(%rax,%rax,1)
    19a0:	xor    %edi,%edi
    19a2:	test   %rdx,%rdx
    19a5:	setg   %dil
    19a9:	sub    %rdi,%rdx
    19ac:	je     19b2 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0xe2>
    19ae:	xor    %edi,%edi
    19b0:	jmp    1934 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x64>
    19b2:	vucomisd %xmm4,%xmm9
    19b6:	jne    19be <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0xee>
    19b8:	jnp    1a5d <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x18d>
    19be:	vmulsd %xmm2,%xmm8,%xmm0
    19c2:	vdivsd %xmm9,%xmm0,%xmm10
    19c7:	mov    $0x1,%dil
    19ca:	vxorpd %xmm8,%xmm8,%xmm8
    19cf:	vmovapd %xmm9,%xmm0
    19d3:	xor    %edx,%edx
    19d5:	jmp    1934 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x64>
    19da:	mov    $0x2a,%ecx
    19df:	vmovsd 0xe621(%rip),%xmm1        # 10008 <_fini+0x9f8>
    19e7:	vmovsd 0xe621(%rip),%xmm2        # 10010 <_fini+0xa00>
    19ef:	vmovsd 0xe621(%rip),%xmm4        # 10018 <_fini+0xa08>
    19f7:	nopw   0x0(%rax,%rax,1)
    1a00:	imul   $0x19660d,%ecx,%ecx
    1a06:	add    $0x3c6ef35f,%ecx
    1a0c:	vcvtsi2sd %rcx,%xmm15,%xmm5
    1a11:	vmulsd %xmm1,%xmm5,%xmm5
    1a15:	vaddsd %xmm2,%xmm5,%xmm5
    1a19:	vmulsd %xmm4,%xmm5,%xmm5
    1a1d:	vaddsd %xmm3,%xmm5,%xmm5
    1a21:	vmulsd %xmm5,%xmm0,%xmm0
    1a25:	dec    %rsi
    1a28:	jne    1a00 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x130>
    1a2a:	jmp    1a3a <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x16a>
    1a2c:	test   %dil,%dil
    1a2f:	je     1a36 <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x166>
    1a31:	vmulsd %xmm10,%xmm9,%xmm8
    1a36:	vmovapd %xmm8,%xmm0
    1a3a:	xor    %esi,%esi
    1a3c:	mov    %r9,0x10(%rax)
    1a40:	mov    %r8,0x18(%rax)
    1a44:	vmovsd %xmm0,0x8(%rax)
    1a49:	and    $0x1,%sil
    1a4d:	mov    %sil,(%rax)
    1a50:	mov    %rdi,0x20(%rax)
    1a54:	mov    %rcx,0x28(%rax)
    1a58:	mov    %dl,0x30(%rax)
    1a5b:	pop    %rcx
    1a5c:	ret
    1a5d:	xor    %edi,%edi
    1a5f:	mov    %rax,(%rsp)
    1a63:	call   1a90 <std::builtin::error::StackTrace::collect_if_enabled(::SIMD[DType.int, 1])>
    1a68:	mov    %rax,%rcx
    1a6b:	mov    (%rsp),%rax
    1a6f:	mov    $0x1,%sil
    1a72:	movabs $0x2000000000000000,%rdi
    1a7c:	mov    $0x33,%r8d
    1a82:	lea    0xe6b7(%rip),%r9        # 10140 <static_string_3a20ef3aad3e5832>
    1a89:	jmp    1a3c <fast::_native_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x16c>
