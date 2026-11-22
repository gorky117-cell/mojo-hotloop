
/tmp/hotloop-provenance/final-performance/origin-1/fast.so:     file format elf64-x86-64


Disassembly of section .text:

00000000000018d0 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])>:
    18d0:	push   %rax
    18d1:	mov    %rdi,%rax
    18d4:	xor    %ecx,%ecx
    18d6:	test   %rsi,%rsi
    18d9:	setle  %dl
    18dc:	jle    1a4a <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x17a>
    18e2:	vmovsd 0xe716(%rip),%xmm3        # 10000 <_fini+0x970>
    18ea:	vxorpd %xmm4,%xmm4,%xmm4
    18ee:	vucomisd %xmm4,%xmm1
    18f2:	jbe    19ed <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x11d>
    18f8:	vsubsd %xmm2,%xmm3,%xmm2
    18fc:	vsubsd %xmm1,%xmm3,%xmm1
    1900:	mov    $0x1,%r9b
    1903:	mov    $0x2a,%edi
    1908:	xor    %r8d,%r8d
    190b:	vmovsd 0xe6f5(%rip),%xmm5        # 10008 <_fini+0x978>
    1913:	vmovsd 0xe6f5(%rip),%xmm6        # 10010 <_fini+0x980>
    191b:	vmovsd 0xe6f5(%rip),%xmm7        # 10018 <_fini+0x988>
    1923:	vmovapd %xmm3,%xmm10
    1927:	vxorpd %xmm8,%xmm8,%xmm8
    192c:	vmovapd %xmm0,%xmm9
    1930:	jmp    194d <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x7d>
    1932:	data16 data16 data16 data16 cs nopw 0x0(%rax,%rax,1)
    1940:	vmovapd %xmm9,%xmm0
    1944:	dec    %rsi
    1947:	je     1a3c <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x16c>
    194d:	imul   $0x19660d,%edi,%edi
    1953:	add    $0x3c6ef35f,%edi
    1959:	vcvtsi2sd %rdi,%xmm15,%xmm11
    195e:	vmulsd %xmm5,%xmm11,%xmm11
    1962:	vaddsd %xmm6,%xmm11,%xmm11
    1966:	vmulsd %xmm7,%xmm11,%xmm11
    196a:	vaddsd %xmm3,%xmm11,%xmm11
    196e:	vmulsd %xmm11,%xmm9,%xmm9
    1973:	test   $0x1,%r9b
    1977:	je     19b0 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0xe0>
    1979:	mov    $0x1,%r9b
    197c:	vucomisd %xmm0,%xmm9
    1980:	ja     1940 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x70>
    1982:	vmulsd %xmm0,%xmm1,%xmm11
    1986:	vucomisd %xmm9,%xmm11
    198b:	jb     1944 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    198d:	vmulsd %xmm9,%xmm10,%xmm8
    1992:	vmulsd %xmm2,%xmm8,%xmm8
    1996:	mov    $0x5,%r8d
    199c:	vxorpd %xmm10,%xmm10,%xmm10
    19a1:	xor    %r9d,%r9d
    19a4:	jmp    1944 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    19a6:	cs nopw 0x0(%rax,%rax,1)
    19b0:	xor    %r9d,%r9d
    19b3:	test   %r8,%r8
    19b6:	setg   %r9b
    19ba:	sub    %r9,%r8
    19bd:	je     19c4 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0xf4>
    19bf:	xor    %r9d,%r9d
    19c2:	jmp    1944 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    19c4:	vucomisd %xmm4,%xmm9
    19c8:	jne    19d0 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x100>
    19ca:	jnp    1a86 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x1b6>
    19d0:	vmulsd %xmm2,%xmm8,%xmm0
    19d4:	vdivsd %xmm9,%xmm0,%xmm10
    19d9:	mov    $0x1,%r9b
    19dc:	vxorpd %xmm8,%xmm8,%xmm8
    19e1:	vmovapd %xmm9,%xmm0
    19e5:	xor    %r8d,%r8d
    19e8:	jmp    1944 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    19ed:	mov    $0x2a,%edi
    19f2:	vmovsd 0xe60e(%rip),%xmm1        # 10008 <_fini+0x978>
    19fa:	vmovsd 0xe60e(%rip),%xmm2        # 10010 <_fini+0x980>
    1a02:	vmovsd 0xe60e(%rip),%xmm4        # 10018 <_fini+0x988>
    1a0a:	nopw   0x0(%rax,%rax,1)
    1a10:	imul   $0x19660d,%edi,%edi
    1a16:	add    $0x3c6ef35f,%edi
    1a1c:	vcvtsi2sd %rdi,%xmm15,%xmm5
    1a21:	vmulsd %xmm1,%xmm5,%xmm5
    1a25:	vaddsd %xmm2,%xmm5,%xmm5
    1a29:	vmulsd %xmm4,%xmm5,%xmm5
    1a2d:	vaddsd %xmm3,%xmm5,%xmm5
    1a31:	vmulsd %xmm5,%xmm0,%xmm0
    1a35:	dec    %rsi
    1a38:	jne    1a10 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x140>
    1a3a:	jmp    1a4a <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x17a>
    1a3c:	test   %r9b,%r9b
    1a3f:	je     1a46 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x176>
    1a41:	vmulsd %xmm10,%xmm9,%xmm8
    1a46:	vmovapd %xmm8,%xmm0
    1a4a:	mov    %dl,%cl
    1a4c:	lea    -0x1(,%rcx,2),%rdi
    1a54:	mov    $0xffffffffffffffff,%r8
    1a5b:	xor    %esi,%esi
    1a5d:	mov    %r11,0x20(%rax)
    1a61:	mov    %r10,0x28(%rax)
    1a65:	vmovsd %xmm0,0x8(%rax)
    1a6a:	and    $0x1,%sil
    1a6e:	mov    %sil,(%rax)
    1a71:	mov    %r9,0x30(%rax)
    1a75:	mov    %rdi,0x10(%rax)
    1a79:	mov    %rcx,0x38(%rax)
    1a7d:	mov    %r8,0x18(%rax)
    1a81:	mov    %dl,0x40(%rax)
    1a84:	pop    %rcx
    1a85:	ret
    1a86:	xor    %edi,%edi
    1a88:	mov    %rax,(%rsp)
    1a8c:	call   1ac0 <std::builtin::error::StackTrace::collect_if_enabled(::SIMD[DType.int, 1])>
    1a91:	mov    %rax,%rcx
    1a94:	mov    (%rsp),%rax
    1a98:	mov    $0x1,%sil
    1a9b:	movabs $0x2000000000000000,%r9
    1aa5:	mov    $0x33,%r10d
    1aab:	lea    0xe67e(%rip),%r11        # 10130 <static_string_3a20ef3aad3e5832>
    1ab2:	jmp    1a5d <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x18d>
